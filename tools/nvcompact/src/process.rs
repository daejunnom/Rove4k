//! Bounded, owned child processes. Limits apply to each child, not an aggregate
//! cgroup; callers also bound job count. No shell parsing is implicit here.
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::io::{Read, Write};
use std::os::fd::AsRawFd;
use std::os::unix::process::{CommandExt, ExitStatusExt};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, OnceLock,
};
use std::time::{Duration, Instant};

static CANCEL: OnceLock<Arc<AtomicBool>> = OnceLock::new();
pub fn install_signal_handlers() -> Result<()> {
    let flag = CANCEL.get_or_init(|| Arc::new(AtomicBool::new(false)));
    for signal in [signal_hook::consts::SIGINT, signal_hook::consts::SIGTERM] {
        signal_hook::flag::register(signal, flag.clone())?;
    }
    Ok(())
}
pub fn cancelled() -> bool {
    CANCEL.get().is_some_and(|v| v.load(Ordering::Relaxed))
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
pub struct Limits {
    pub seconds: f64,
    pub memory_bytes: u64,
    pub output_bytes: usize,
    pub cpu_seconds: u64,
    pub file_bytes: u64,
}
impl Default for Limits {
    fn default() -> Self {
        Self {
            seconds: 60.0,
            memory_bytes: 1 << 30,
            output_bytes: 16 << 20,
            cpu_seconds: 120,
            file_bytes: 64 << 20,
        }
    }
}
impl Limits {
    pub fn validate(&self) -> Result<()> {
        if !self.seconds.is_finite()
            || self.seconds <= 0.0
            || self.seconds > 86400.0
            || self.memory_bytes == 0
            || self.output_bytes == 0
            || self.cpu_seconds == 0
            || self.file_bytes == 0
        {
            bail!("process limits must be finite and positive (wall <= 86400s)");
        }
        Ok(())
    }
}

/// Only async-signal-safe libc calls run after fork. Captures are plain values;
/// the closure never allocates, formats errors, locks, or changes parent limits.
pub fn configure(command: &mut Command, limits: &Limits) -> Result<()> {
    limits.validate()?;
    command.process_group(0);
    let amounts = [
        (libc::RLIMIT_AS, limits.memory_bytes),
        (libc::RLIMIT_CPU, limits.cpu_seconds),
        (libc::RLIMIT_FSIZE, limits.file_bytes),
        (libc::RLIMIT_CORE, 0),
    ];
    unsafe {
        command.pre_exec(move || {
            for (kind, value) in amounts {
                let mut old = libc::rlimit {
                    rlim_cur: 0,
                    rlim_max: 0,
                };
                if libc::getrlimit(kind, &mut old) != 0 {
                    return Err(std::io::Error::last_os_error());
                }
                let cap = (value as libc::rlim_t).min(old.rlim_cur).min(old.rlim_max);
                let new = libc::rlimit {
                    rlim_cur: cap,
                    rlim_max: cap,
                };
                if libc::setrlimit(kind, &new) != 0 {
                    return Err(std::io::Error::last_os_error());
                }
            }
            Ok(())
        });
    }
    Ok(())
}

pub fn nonblocking(fd: std::os::fd::RawFd) -> std::io::Result<()> {
    // fcntl only changes the owned pipe's open-file status flags.
    unsafe {
        let old = libc::fcntl(fd, libc::F_GETFL);
        if old == -1 || libc::fcntl(fd, libc::F_SETFL, old | libc::O_NONBLOCK) == -1 {
            return Err(std::io::Error::last_os_error());
        }
    }
    Ok(())
}

/// Owns only a group created for this child. Drop kills the group and reaps the
/// leader even on an early error. It does not scan or signal unrelated PIDs.
pub struct OwnedChild {
    pub child: Child,
    pub pgid: i32,
}
impl OwnedChild {
    pub fn new(child: Child) -> Self {
        let pgid = child.id() as i32;
        Self { child, pgid }
    }
    pub fn kill_group(&mut self) {
        unsafe {
            libc::kill(-self.pgid, libc::SIGKILL);
        }
    }
}
impl Drop for OwnedChild {
    fn drop(&mut self) {
        self.kill_group();
        let _ = self.child.wait();
    }
}

#[derive(Debug)]
pub struct Output {
    pub code: i32,
    pub stdout: Vec<u8>,
    pub stderr: Vec<u8>,
    pub wall_seconds: f64,
    pub timed_out: bool,
    pub output_limited: bool,
}
impl Output {
    pub fn success(&self) -> bool {
        self.code == 0 && !self.timed_out && !self.output_limited
    }
    pub fn check(&self, label: &str) -> Result<()> {
        if !self.success() {
            bail!(
                "{label} failed (exit {}, timeout {}, output limit {}): {}",
                self.code,
                self.timed_out,
                self.output_limited,
                String::from_utf8_lossy(&self.stderr)
            );
        }
        Ok(())
    }
}

fn drain<R: Read>(
    pipe: &mut R,
    out: &mut Vec<u8>,
    remaining: &mut usize,
) -> std::io::Result<(bool, bool)> {
    let mut buf = [0u8; 8192];
    // A finite read batch prevents a continuously chatty child starving timeout.
    for _ in 0..32 {
        match pipe.read(&mut buf) {
            Ok(0) => return Ok((true, false)),
            Ok(n) => {
                let keep = n.min(*remaining);
                out.extend_from_slice(&buf[..keep]);
                *remaining -= keep;
                if keep < n {
                    return Ok((false, true));
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => break,
            Err(e) if e.kind() == std::io::ErrorKind::Interrupted => continue,
            Err(e) => return Err(e),
        }
    }
    Ok((false, false))
}

pub fn run(argv: &[String], input: &[u8], cwd: &Path, limits: &Limits) -> Result<Output> {
    run_with_env(argv, input, cwd, limits, None)
}

pub fn run_with_env(
    argv: &[String],
    input: &[u8],
    cwd: &Path,
    limits: &Limits,
    environment: Option<&std::collections::BTreeMap<String, String>>,
) -> Result<Output> {
    if argv.is_empty() {
        bail!("empty command");
    }
    limits.validate()?;
    if cancelled() {
        bail!("cancelled before process start");
    }
    let started = Instant::now();
    let mut command = Command::new(&argv[0]);
    command
        .args(&argv[1..])
        .current_dir(cwd)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    if let Some(env) = environment {
        command.env_clear().envs(env);
    }
    configure(&mut command, limits)?;
    let mut owned = OwnedChild::new(
        command
            .spawn()
            .with_context(|| format!("start {}", argv[0]))?,
    );
    let mut stdin = owned.child.stdin.take();
    let mut stdout = owned.child.stdout.take().context("missing stdout pipe")?;
    let mut stderr = owned.child.stderr.take().context("missing stderr pipe")?;
    for fd in [
        stdout.as_raw_fd(),
        stderr.as_raw_fd(),
        stdin.as_ref().unwrap().as_raw_fd(),
    ] {
        nonblocking(fd)?;
    }
    let mut a = Vec::new();
    let mut b = Vec::new();
    let mut sent = 0;
    let mut eof_a = false;
    let mut eof_b = false;
    let mut remaining = limits.output_bytes;
    let mut timed_out = false;
    let mut limited = false;
    let mut status = None;
    loop {
        if started.elapsed().as_secs_f64() > limits.seconds || cancelled() {
            timed_out = true;
            owned.kill_group();
            break;
        }
        if let Some(pipe) = stdin.as_mut() {
            if sent == input.len() {
                stdin.take();
            } else {
                match pipe.write(&input[sent..input.len().min(sent + 65536)]) {
                    Ok(n) => sent += n,
                    Err(e)
                        if e.kind() == std::io::ErrorKind::WouldBlock
                            || e.kind() == std::io::ErrorKind::Interrupted => {}
                    Err(e) if e.kind() == std::io::ErrorKind::BrokenPipe => {
                        stdin.take();
                    }
                    Err(e) => return Err(e.into()),
                }
            }
        }
        if !eof_a {
            let (e, l) = drain(&mut stdout, &mut a, &mut remaining)?;
            eof_a = e;
            limited |= l;
        }
        if !eof_b {
            let (e, l) = drain(&mut stderr, &mut b, &mut remaining)?;
            eof_b = e;
            limited |= l;
        }
        if limited {
            owned.kill_group();
            break;
        }
        if status.is_none() {
            status = owned.child.try_wait()?;
        }
        if status.is_some() && eof_a && eof_b {
            break;
        }
        std::thread::sleep(Duration::from_millis(2));
    }
    if timed_out || limited {
        stdin.take();
        owned.kill_group();
    }
    let exit = match status {
        Some(s) => s,
        None => owned.child.wait()?,
    };
    let code = if timed_out {
        124
    } else if limited {
        125
    } else {
        exit.code().unwrap_or_else(|| -exit.signal().unwrap_or(1))
    };
    Ok(Output {
        code,
        stdout: a,
        stderr: b,
        wall_seconds: started.elapsed().as_secs_f64(),
        timed_out,
        output_limited: limited,
    })
}

/// Resolve a declared tool without executing a version probe. Keep invocation
/// path and canonical target separately when recording a recipe.
pub fn resolve_tool(name: &str) -> Result<PathBuf> {
    let path = Path::new(name);
    if path.components().count() > 1 {
        if !path.is_file() {
            bail!("tool does not exist: {name}");
        }
        return Ok(if path.is_absolute() {
            path.to_path_buf()
        } else {
            std::env::current_dir()?.join(path)
        });
    }
    if let Some(paths) = std::env::var_os("PATH") {
        for directory in std::env::split_paths(&paths) {
            let candidate = directory.join(name);
            if candidate.is_file() {
                use std::os::unix::fs::PermissionsExt;
                if candidate.metadata()?.permissions().mode() & 0o111 != 0 {
                    return Ok(if candidate.is_absolute() {
                        candidate
                    } else {
                        std::env::current_dir()?.join(candidate)
                    });
                }
            }
        }
    }
    bail!("tool not found on PATH: {name}")
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn argv_binary_streams_and_exit_are_observed() {
        let a = run(
            &[
                "sh".into(),
                "-c".into(),
                "cat; printf diagnostic >&2; exit 7".into(),
            ],
            b"a\0b\n",
            Path::new("/tmp"),
            &Limits::default(),
        )
        .unwrap();
        assert_eq!(a.stdout, b"a\0b\n");
        assert_eq!(a.stderr, b"diagnostic");
        assert_eq!(a.code, 7);
    }
    #[test]
    fn wall_and_output_bounds_apply() {
        let limits = Limits {
            seconds: 0.05,
            ..Limits::default()
        };
        let a = run(
            &["sh".into(), "-c".into(), "sleep 5".into()],
            b"",
            Path::new("/tmp"),
            &limits,
        )
        .unwrap();
        assert!(a.timed_out);
        assert!(a.wall_seconds < 2.0);
        let limits = Limits {
            output_bytes: 100,
            ..Limits::default()
        };
        let a = run(
            &["sh".into(), "-c".into(), "yes x".into()],
            b"",
            Path::new("/tmp"),
            &limits,
        )
        .unwrap();
        assert!(a.output_limited);
        assert_eq!(a.stdout.len() + a.stderr.len(), 100);
    }
}
