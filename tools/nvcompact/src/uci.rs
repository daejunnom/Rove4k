//! Finite protocol and independent move-legality probes for complete artifacts.
//! The cozy-chess oracle runs in this development tool, never in the submission.
use anyhow::{bail, Context, Result};
use cozy_chess::{Board, Move, Piece, Square};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::VecDeque;
use std::fmt;
use std::fs;
use std::io::{Read, Write};
use std::os::fd::AsRawFd;
use std::os::unix::process::{CommandExt, ExitStatusExt};
use std::path::{Path, PathBuf};
use std::process::{ChildStderr, ChildStdin, ChildStdout, Command, Stdio};
use std::time::{Duration, Instant};

use crate::process::{self, Limits, OwnedChild};

pub const FORMAT: &str = "nvcompact.uci.v2";
pub const TCEC_SOURCE: &str = "https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853";

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct UciConfig {
    pub profile: String,
    pub extensions: bool,
    pub quick: bool,
    /// Empty selects the normal corpus; an explicit subset is reported as such.
    pub case_ids: Vec<String>,
    pub artifact_path: Option<String>,
    /// Used by a resource plan to preserve argv[0] after resolving its executable.
    pub invocation_argv0: Option<String>,
    pub startup_seconds: f64,
    pub ready_seconds: f64,
    pub search_seconds: f64,
    pub stop_seconds: f64,
    pub quit_seconds: f64,
    pub cleanup_seconds: f64,
    pub max_seconds: f64,
    pub clock_ms: u64,
    pub clock_grace_ms: u64,
    pub increment_ms: u64,
    pub movetime_ms: u64,
    pub depth: u32,
    pub nodes: u64,
    pub threads: u32,
    pub hash_mb: u64,
    pub preserve_engine_options: bool,
    pub max_output_bytes: usize,
    pub max_line_bytes: usize,
    pub max_transcript_bytes: usize,
    pub memory_bytes: u64,
    pub cpu_seconds: u64,
    pub file_bytes: u64,
}

impl Default for UciConfig {
    fn default() -> Self {
        Self {
            profile: "tcec4k".into(),
            extensions: false,
            quick: false,
            case_ids: Vec::new(),
            artifact_path: None,
            invocation_argv0: None,
            startup_seconds: 60.0,
            ready_seconds: 5.0,
            search_seconds: 5.0,
            stop_seconds: 2.0,
            quit_seconds: 2.0,
            cleanup_seconds: 5.0,
            max_seconds: 180.0,
            clock_ms: 2000,
            clock_grace_ms: 1000,
            increment_ms: 0,
            movetime_ms: 100,
            depth: 3,
            nodes: 1000,
            threads: 1,
            hash_mb: 16,
            preserve_engine_options: true,
            max_output_bytes: 2 << 20,
            max_line_bytes: 65536,
            max_transcript_bytes: 256 << 10,
            memory_bytes: 1 << 30,
            cpu_seconds: 120,
            file_bytes: 64 << 20,
        }
    }
}

impl UciConfig {
    pub fn validate(&self) -> Result<()> {
        if self.profile != "tcec4k" && self.profile != "uci" {
            bail!("profile must be tcec4k or uci");
        }
        if self.quick && !self.case_ids.is_empty() {
            bail!("choose quick or explicit case_ids, not both");
        }
        for (index, id) in self.case_ids.iter().enumerate() {
            if !START_CASES.iter().any(|(known, _)| id == known) {
                bail!("unknown core case_id: {id}");
            }
            if self.case_ids[..index].contains(id) {
                bail!("duplicate core case_id: {id}");
            }
        }
        for (name, value) in [
            ("startup_seconds", self.startup_seconds),
            ("ready_seconds", self.ready_seconds),
            ("search_seconds", self.search_seconds),
            ("stop_seconds", self.stop_seconds),
            ("quit_seconds", self.quit_seconds),
            ("cleanup_seconds", self.cleanup_seconds),
            ("max_seconds", self.max_seconds),
        ] {
            if !value.is_finite() || value <= 0.0 || value > 86400.0 {
                bail!("{name} must be positive and finite, at most 86400 seconds");
            }
        }
        if self.startup_seconds > 60.0 {
            bail!("startup_seconds exceeds TCEC's 60-second ceiling");
        }
        if self.cleanup_seconds > 60.0 {
            bail!("cleanup_seconds exceeds 60 seconds");
        }
        if self.clock_ms == 0
            || self.movetime_ms == 0
            || self.depth == 0
            || self.nodes == 0
            || self.threads == 0
            || self.hash_mb == 0
            || self.max_line_bytes == 0
            || self.max_transcript_bytes == 0
        {
            bail!("integer UCI budgets must be positive");
        }
        if self.clock_ms.checked_add(self.clock_grace_ms).is_none() {
            bail!("clock budget overflow");
        }
        if self
            .invocation_argv0
            .as_ref()
            .is_some_and(|v| v.is_empty() || v.contains('\0'))
        {
            bail!("invalid invocation argv[0]");
        }
        self.limits().validate()
    }

    pub fn limits(&self) -> Limits {
        Limits {
            seconds: self.max_seconds,
            memory_bytes: self.memory_bytes,
            output_bytes: self.max_output_bytes,
            cpu_seconds: self.cpu_seconds,
            file_bytes: self.file_bytes,
        }
    }
}

#[derive(Debug)]
struct ProbeError {
    kind: &'static str,
    message: String,
}
impl fmt::Display for ProbeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.message)
    }
}
impl std::error::Error for ProbeError {}
fn error(kind: &'static str, message: impl Into<String>) -> anyhow::Error {
    ProbeError {
        kind,
        message: message.into(),
    }
    .into()
}
fn failure(err: &anyhow::Error) -> (&str, &str) {
    let kind = err.downcast_ref::<ProbeError>().map_or("io", |e| e.kind);
    (
        if matches!(kind, "budget" | "probe_budget" | "cancelled") {
            "incomplete"
        } else {
            "fail"
        },
        kind,
    )
}

fn group_exists(pgid: i32) -> bool {
    // Only the group created for our own child is addressed. No /proc PID scan.
    unsafe {
        libc::kill(-pgid, 0) == 0
            || std::io::Error::last_os_error().raw_os_error() == Some(libc::EPERM)
    }
}

struct Session {
    child: OwnedChild,
    stdin: ChildStdin,
    stdout: ChildStdout,
    stderr: ChildStderr,
    config: UciConfig,
    started: Instant,
    deadline: Instant,
    stdout_eof: bool,
    stderr_eof: bool,
    buffer: Vec<u8>,
    lines: VecDeque<String>,
    transcript: Vec<Value>,
    transcript_bytes: usize,
    omitted: usize,
    stdout_bytes: usize,
    stderr_bytes: usize,
    stderr_tail: Vec<u8>,
    cleanup: Value,
}

impl Session {
    fn spawn(
        command: &[String],
        config: &UciConfig,
        deadline: Instant,
        cwd: &Path,
    ) -> Result<Self> {
        if process::cancelled() {
            return Err(error("cancelled", "cancelled before engine spawn"));
        }
        let started = Instant::now();
        fs::create_dir(cwd.join("tmp"))?;
        let mut cmd = Command::new(&command[0]);
        cmd.args(&command[1..])
            .current_dir(cwd)
            .env("TMPDIR", cwd.join("tmp"))
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        if let Some(argv0) = &config.invocation_argv0 {
            cmd.arg0(argv0);
        }
        process::configure(&mut cmd, &config.limits())?;
        let mut child = OwnedChild::new(cmd.spawn().context("launch UCI engine")?);
        let stdin = child.child.stdin.take().context("missing engine stdin")?;
        let stdout = child.child.stdout.take().context("missing engine stdout")?;
        let stderr = child.child.stderr.take().context("missing engine stderr")?;
        for fd in [stdin.as_raw_fd(), stdout.as_raw_fd(), stderr.as_raw_fd()] {
            process::nonblocking(fd)?;
        }
        Ok(Self {
            child,
            stdin,
            stdout,
            stderr,
            config: config.clone(),
            started,
            deadline,
            stdout_eof: false,
            stderr_eof: false,
            buffer: Vec::new(),
            lines: VecDeque::new(),
            transcript: Vec::new(),
            transcript_bytes: 0,
            omitted: 0,
            stdout_bytes: 0,
            stderr_bytes: 0,
            stderr_tail: Vec::new(),
            cleanup: json!({}),
        })
    }

    fn record(&mut self, direction: &str, text: &str) {
        if self.transcript_bytes.saturating_add(text.len()) <= self.config.max_transcript_bytes {
            self.transcript
                .push(json!({"at_ms": self.started.elapsed().as_secs_f64()*1000.0,
                "direction": direction, "text": text}));
            self.transcript_bytes += text.len();
        } else {
            self.omitted += 1;
        }
    }

    fn bound(&self, seconds: f64) -> Instant {
        self.deadline
            .min(Instant::now() + Duration::from_secs_f64(seconds))
    }

    fn check_deadline(&self, deadline: Instant) -> Result<()> {
        if process::cancelled() {
            return Err(error("cancelled", "verifier cancelled"));
        }
        if Instant::now() >= self.deadline {
            return Err(error("budget", "total verifier budget exhausted"));
        }
        if Instant::now() >= deadline {
            return Err(error("timeout", "response deadline exceeded"));
        }
        Ok(())
    }

    fn send(&mut self, text: &str) -> Result<()> {
        if !text.is_ascii() || text.contains(['\n', '\r', '\0']) {
            bail!("UCI command must be one ASCII line");
        }
        self.record("send", text);
        let data = format!("{text}\n");
        let mut sent = 0;
        let deadline = self.bound(self.config.ready_seconds);
        while sent < data.len() {
            self.check_deadline(deadline)?;
            if let Some(code) = self.child.child.try_wait()? {
                return Err(error(
                    "exit",
                    format!("engine exited before command {text:?}: {code}"),
                ));
            }
            match self.stdin.write(&data.as_bytes()[sent..]) {
                Ok(0) => return Err(error("exit", "engine stdin accepted zero bytes")),
                Ok(n) => sent += n,
                Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                    self.pump()?;
                    std::thread::sleep(Duration::from_millis(2));
                }
                Err(e) if e.kind() == std::io::ErrorKind::Interrupted => {}
                Err(e) if e.kind() == std::io::ErrorKind::BrokenPipe => {
                    return Err(error("exit", "engine closed stdin"))
                }
                Err(e) => return Err(e.into()),
            }
        }
        Ok(())
    }

    fn append_stdout(&mut self, bytes: &[u8]) -> Result<()> {
        self.stdout_bytes = self.stdout_bytes.saturating_add(bytes.len());
        self.check_output()?;
        self.buffer.extend_from_slice(bytes);
        let mut consumed = 0;
        while let Some(offset) = self.buffer[consumed..].iter().position(|b| *b == b'\n') {
            let end = consumed + offset;
            if end - consumed > self.config.max_line_bytes {
                return Err(error("output_limit", "stdout line exceeds limit"));
            }
            let line = std::str::from_utf8(&self.buffer[consumed..end])
                .map_err(|_| error("protocol", "stdout protocol line is not UTF-8"))?;
            if line.contains('\0') {
                return Err(error("protocol", "NUL byte in protocol line"));
            }
            self.lines.push_back(line.trim().to_owned());
            consumed = end + 1;
        }
        if consumed != 0 {
            self.buffer.drain(..consumed);
        }
        if self.buffer.len() > self.config.max_line_bytes {
            return Err(error(
                "output_limit",
                "unterminated stdout line exceeds limit",
            ));
        }
        Ok(())
    }

    fn check_output(&self) -> Result<()> {
        if self.stdout_bytes.saturating_add(self.stderr_bytes) > self.config.max_output_bytes {
            return Err(error(
                "output_limit",
                "combined stdout/stderr exceeds limit",
            ));
        }
        Ok(())
    }

    fn pump(&mut self) -> Result<()> {
        let mut buf = [0u8; 8192];
        for _ in 0..32 {
            if self.stdout_eof {
                break;
            }
            match self.stdout.read(&mut buf) {
                Ok(0) => {
                    self.stdout_eof = true;
                    break;
                }
                Ok(n) => self.append_stdout(&buf[..n])?,
                Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => break,
                Err(e) if e.kind() == std::io::ErrorKind::Interrupted => {}
                Err(e) => return Err(e.into()),
            }
        }
        for _ in 0..32 {
            if self.stderr_eof {
                break;
            }
            match self.stderr.read(&mut buf) {
                Ok(0) => {
                    self.stderr_eof = true;
                    break;
                }
                Ok(n) => {
                    self.stderr_bytes = self.stderr_bytes.saturating_add(n);
                    self.check_output()?;
                    self.stderr_tail.extend_from_slice(&buf[..n]);
                    if self.stderr_tail.len() > 16384 {
                        self.stderr_tail.drain(..self.stderr_tail.len() - 16384);
                    }
                }
                Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => break,
                Err(e) if e.kind() == std::io::ErrorKind::Interrupted => {}
                Err(e) => return Err(e.into()),
            }
        }
        Ok(())
    }

    fn next_line(&mut self, deadline: Instant) -> Result<String> {
        loop {
            self.check_deadline(deadline)?;
            if let Some(line) = self.lines.pop_front() {
                self.record("receive", &line);
                return Ok(line);
            }
            self.pump()?;
            if !self.lines.is_empty() {
                continue;
            }
            if let Some(status) = self.child.child.try_wait()? {
                return Err(error(
                    "exit",
                    format!("engine leader exited awaiting response: {status}"),
                ));
            }
            if self.stdout_eof {
                return Err(error(
                    "exit",
                    if self.buffer.is_empty() {
                        "engine stdout closed"
                    } else {
                        "stdout ended in an unterminated protocol line"
                    },
                ));
            }
            std::thread::sleep(Duration::from_millis(2));
        }
    }

    fn wait_token(&mut self, token: &str, deadline: Instant) -> Result<Vec<String>> {
        let mut lines = Vec::new();
        loop {
            let line = self.next_line(deadline)?;
            if line == token {
                lines.push(line);
                return Ok(lines);
            }
            if line.starts_with("bestmove") {
                return Err(error(
                    "protocol",
                    format!("unsolicited or duplicate bestmove waiting for {token}"),
                ));
            }
            if line.starts_with(&format!("{token} ")) {
                return Err(error(
                    "protocol",
                    format!("malformed acknowledgement: {line}"),
                ));
            }
            lines.push(line);
        }
    }

    fn ready(&mut self) -> Result<()> {
        self.send("isready")?;
        self.wait_token("readyok", self.bound(self.config.ready_seconds))?;
        Ok(())
    }

    fn bestmove(&mut self, board: &Board, seconds: f64) -> Result<Value> {
        let deadline = self.bound(seconds);
        let mut last_info = Value::Null;
        loop {
            let line = self.next_line(deadline)?;
            if line.starts_with("bestmove") {
                let mut answer = validate_bestmove(&line, board)?;
                answer["last_info"] = last_info;
                return Ok(answer);
            }
            if line.starts_with("info ") {
                last_info = json!(line);
            }
        }
    }

    fn quit(&mut self) -> Result<Value> {
        self.quit_state(false)
    }

    fn quit_state(&mut self, search_pending: bool) -> Result<Value> {
        self.send("quit")?;
        let deadline = self.bound(self.config.quit_seconds);
        let status = loop {
            self.check_deadline(deadline)?;
            self.pump()?;
            if !search_pending && self.lines.iter().any(|s| s.starts_with("bestmove")) {
                return Err(error(
                    "protocol",
                    "unsolicited bestmove after the final readiness boundary",
                ));
            }
            if let Some(code) = self.child.child.try_wait()? {
                break code;
            }
            std::thread::sleep(Duration::from_millis(2));
        };
        let cleanup_started = Instant::now();
        let immediate = group_exists(self.child.pgid);
        let cleanup_deadline = self.bound(self.config.cleanup_seconds);
        while group_exists(self.child.pgid)
            && Instant::now() < cleanup_deadline
            && !process::cancelled()
        {
            self.pump()?;
            std::thread::sleep(Duration::from_millis(5));
        }
        let remains = group_exists(self.child.pgid);
        self.cleanup = json!({"quit_returncode": status.code(), "quit_signal": status.signal(),
            "process_group_exists_immediately_after_quit": immediate,
            "process_group_exists_after_quit": remains,
            "cleanup_wait_ms": cleanup_started.elapsed().as_secs_f64()*1000.0,
            "cleanup_grace_seconds": self.config.cleanup_seconds,
            "scope": "owned original process group; detached sessions and global filesystem not audited"});
        if process::cancelled() {
            return Err(error("cancelled", "cancelled during cleanup"));
        }
        if remains {
            return Err(error(
                "cleanup",
                "owned engine process group remains after quit and cleanup grace",
            ));
        }
        if !status.success() {
            return Err(error("exit", format!("nonzero exit after quit: {status}")));
        }
        Ok(self.cleanup.clone())
    }

    fn close(&mut self) {
        let forced = group_exists(self.child.pgid);
        self.child.kill_group();
        let status = self.child.child.wait();
        self.cleanup["forced_cleanup"] = json!(forced);
        if let Ok(code) = status {
            self.cleanup["returncode"] = json!(code.code());
            self.cleanup["signal"] = json!(code.signal());
        }
    }

    fn summary(&self, phase: &str, leftovers: Value) -> Value {
        json!({"phase": phase, "output_bytes": {"stdout": self.stdout_bytes, "stderr": self.stderr_bytes},
            "transcript": self.transcript, "omitted_transcript_lines": self.omitted,
            "stderr_tail": String::from_utf8_lossy(&self.stderr_tail),
            "cleanup": self.cleanup, "working_directory_leftovers": leftovers})
    }
}

/// Convert standard UCI castling to cozy-chess's king-to-rook representation.
/// Accepting e1h1 in a standard-chess UCI probe would hide a protocol defect.
pub fn parse_standard_move(board: &Board, text: &str) -> Result<Move> {
    if !text.is_ascii() || !(text.len() == 4 || text.len() == 5) {
        bail!("invalid long algebraic move: {text}");
    }
    let mut mv: Move = text
        .parse()
        .map_err(|_| anyhow::anyhow!("invalid UCI move: {text}"))?;
    if board.piece_on(mv.from) == Some(Piece::King) {
        if board.color_on(mv.to) == Some(board.side_to_move()) {
            bail!("nonstandard king-to-rook castling in UCI: {text}");
        }
        mv.to = match (mv.from, mv.to) {
            (Square::E1, Square::G1) => Square::H1,
            (Square::E1, Square::C1) => Square::A1,
            (Square::E8, Square::G8) => Square::H8,
            (Square::E8, Square::C8) => Square::A8,
            _ => mv.to,
        };
    }
    if !board.is_legal(mv) {
        bail!("illegal UCI move {text} for {board}");
    }
    Ok(mv)
}

pub fn validate_bestmove(line: &str, board: &Board) -> Result<Value> {
    let words: Vec<_> = line.split_whitespace().collect();
    if !matches!(words.len(), 2 | 4)
        || words[0] != "bestmove"
        || (words.len() == 4 && words[2] != "ponder")
    {
        return Err(error("protocol", format!("malformed bestmove: {line}")));
    }
    if words[1] == "0000" {
        let mut any = false;
        board.generate_moves(|moves| {
            any = !moves.is_empty();
            any
        });
        if any || words.len() == 4 {
            return Err(error(
                "protocol",
                "null bestmove with legal moves, or ponder after null",
            ));
        }
        return Ok(json!({"bestmove": "0000", "legal": true, "terminal": true}));
    }
    let mv = parse_standard_move(board, words[1]).map_err(|e| error("legality", e.to_string()))?;
    let mut out = json!({"bestmove": words[1], "legal": true, "terminal": false});
    if words.len() == 4 {
        let mut after = board.clone();
        after.play(mv);
        parse_standard_move(&after, words[3])
            .map_err(|e| error("legality", format!("illegal ponder: {e}")))?;
        out["ponder"] = json!(words[3]);
    }
    Ok(out)
}

pub const START_CASES: &[(&str, &str)] = &[
    ("startpos_white", ""),
    ("startpos_black", "e2e4"),
    (
        "castling_history",
        "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1",
    ),
    ("en_passant_history", "e2e4 a7a6 e4e5 d7d5 e5d6"),
    (
        "middlegame_history",
        "e2e4 e7e5 g1f3 b8c6 f1c4 g8f6 d2d3 f8c5 c1g5 d7d6 b1c3 e8g8",
    ),
    (
        "promotion_history",
        "a2a4 h7h5 a4a5 h5h4 a5a6 h4h3 a6b7 h3g2 b7a8q g2h1q",
    ),
];

fn selected_cases(config: &UciConfig) -> Vec<(&'static str, &'static str)> {
    START_CASES
        .iter()
        .copied()
        .take(if config.quick { 3 } else { START_CASES.len() })
        .filter(|(name, _)| {
            config.case_ids.is_empty() || config.case_ids.iter().any(|id| id == name)
        })
        .collect()
}

fn board_start(moves: &str) -> Result<Board> {
    let mut board = Board::default();
    for word in moves.split_whitespace() {
        let mv = parse_standard_move(&board, word)?;
        board.play(mv);
    }
    Ok(board)
}

fn checked<T>(
    cases: &mut Vec<Value>,
    id: &str,
    requirement: &str,
    op: impl FnOnce() -> Result<T>,
) -> Result<T>
where
    T: Serialize,
{
    let started = Instant::now();
    let result = op();
    let mut item = json!({"id": id, "requirement": requirement, "elapsed_ms": started.elapsed().as_secs_f64()*1000.0});
    match &result {
        Ok(detail) => {
            item["status"] = json!("pass");
            item["detail"] = serde_json::to_value(detail)?;
        }
        Err(err) => {
            let (status, kind) = failure(err);
            item["status"] = json!(status);
            item["kind"] = json!(kind);
            item["error"] = json!(err.to_string());
        }
    }
    cases.push(item);
    result
}

fn parse_option(line: &str) -> Result<Value> {
    let re = regex::Regex::new(
        r"^option\s+name\s+(.+?)\s+type\s+(check|spin|combo|button|string)(?:\s+(.*))?$",
    )?;
    let cap = re.captures(line).context("malformed advertised option")?;
    let kind = &cap[2];
    let rest = cap.get(3).map_or("", |c| c.as_str());
    let attrs = regex::Regex::new(r"(?:^|\s)(default|min|max|var)(?:\s|$)")?;
    let matches: Vec<_> = attrs.captures_iter(rest).collect();
    if matches.first().map_or(!rest.trim().is_empty(), |m| {
        !rest[..m.get(0).unwrap().start()].trim().is_empty()
    }) {
        bail!("unrecognized option attributes");
    }
    let mut value = json!({"name": &cap[1], "type": kind});
    let mut variants = Vec::new();
    for (i, m) in matches.iter().enumerate() {
        let start = m.get(0).unwrap().end();
        let end = matches
            .get(i + 1)
            .map_or(rest.len(), |c| c.get(0).unwrap().start());
        let key = &m[1];
        let text = rest[start..end].trim();
        if key == "var" {
            variants.push(text.to_owned());
        } else {
            if value.get(key).is_some() {
                bail!("duplicate option attribute: {key}");
            }
            value[key] = json!(text);
        }
    }
    if !variants.is_empty() {
        value["var"] = json!(variants);
    }
    if kind == "spin" {
        for key in ["min", "default", "max"] {
            let n: i64 = value[key]
                .as_str()
                .context("spin option missing min/default/max")?
                .parse()?;
            value[key] = json!(n);
        }
        if !(value["min"].as_i64() <= value["default"].as_i64()
            && value["default"].as_i64() <= value["max"].as_i64())
        {
            bail!("spin default outside range");
        }
    }
    if kind == "check" && !matches!(value["default"].as_str(), Some("true" | "false")) {
        bail!("invalid check default");
    }
    if kind == "combo"
        && !variants
            .iter()
            .any(|v| Some(v.as_str()) == value["default"].as_str())
    {
        bail!("combo default not advertised");
    }
    Ok(value)
}

fn handshake(session: &mut Session, config: &UciConfig) -> Result<Value> {
    let deadline = session
        .deadline
        .min(session.started + Duration::from_secs_f64(config.startup_seconds));
    session.send("uci")?;
    let lines = session.wait_token("uciok", deadline)?;
    let mut identity = json!({});
    let mut options: Vec<Value> = Vec::new();
    let mut errors = Vec::new();
    for line in &lines {
        for key in ["name", "author"] {
            if let Some(value) = line.strip_prefix(&format!("id {key} ")) {
                identity[key] = json!(value);
            }
        }
        if line.starts_with("option") {
            match parse_option(line) {
                Ok(value)
                    if !options.iter().any(|v| {
                        v["name"]
                            .as_str()
                            .unwrap()
                            .eq_ignore_ascii_case(value["name"].as_str().unwrap())
                    }) =>
                {
                    options.push(value)
                }
                Ok(_) => errors.push(format!("duplicate option: {line}")),
                Err(e) => errors.push(format!("{line}: {e}")),
            }
        }
    }
    let mut configured = Vec::new();
    for option in &options {
        let name = option["name"].as_str().unwrap();
        if config.preserve_engine_options {
            configured.push(json!({"name": name, "status": "preserved", "advertised_default": option["default"]}));
            continue;
        }
        let lower = name.to_ascii_lowercase();
        let selected = if option["type"] == "spin"
            && matches!(lower.as_str(), "hash" | "threads" | "multipv")
        {
            let requested = match lower.as_str() {
                "hash" => config.hash_mb,
                "threads" => config.threads as u64,
                _ => 1,
            }
            .min(i64::MAX as u64) as i64;
            let low = option["min"].as_i64().unwrap();
            let high = option["max"].as_i64().unwrap();
            if low > requested {
                configured.push(json!({"name": name, "status": "not_set", "reason": "minimum exceeds requested resource budget"}));
                None
            } else {
                Some(requested.min(high).max(low).to_string())
            }
        } else if option["type"] == "check" && matches!(lower.as_str(), "ponder" | "ownbook") {
            Some("false".into())
        } else {
            None
        };
        if let Some(value) = selected {
            session.send(&format!("setoption name {name} value {value}"))?;
            configured.push(json!({"name": name, "value": value, "status": "sent"}));
        }
    }
    session.send("isready")?;
    session.wait_token("readyok", deadline)?;
    Ok(
        json!({"identity": identity, "options": options, "option_errors": errors,
        "configured_options": configured, "ready_after_launch_ms": session.started.elapsed().as_secs_f64()*1000.0}),
    )
}

fn search(
    session: &mut Session,
    board: &Board,
    position: &str,
    go: &str,
    seconds: f64,
    engine_deadline_seconds: Option<f64>,
) -> Result<Value> {
    session.send(position)?;
    session.ready()?;
    let started = Instant::now();
    session.send(go)?;
    let mut result = session.bestmove(board, seconds).map_err(|err| {
        if err.downcast_ref::<ProbeError>().is_some_and(|e| e.kind == "timeout")
            && engine_deadline_seconds.is_none_or(|full| seconds < full) {
            error("probe_budget", format!("verifier search observation budget ({seconds}s) ended before any applicable engine clock deadline ({engine_deadline_seconds:?}); no engine time-forfeit conclusion"))
        } else { err }
    })?;
    result["position"] = json!(position);
    result["fen"] = json!(board.to_string());
    result["go"] = json!(go);
    result["search_elapsed_ms"] = json!(started.elapsed().as_secs_f64() * 1000.0);
    result["response_budget_seconds"] = json!(seconds);
    result["engine_clock_with_grace_seconds"] = json!(engine_deadline_seconds);
    session.ready()?;
    Ok(result)
}

fn core(
    session: &mut Session,
    config: &UciConfig,
    cases: &mut Vec<Value>,
    observations: &mut Vec<Value>,
    handshakes: &mut Vec<Value>,
) -> Result<()> {
    handshakes.push(checked(cases, "handshake", "tcec4k", || {
        handshake(session, config)
    })?);
    for (label, command) in [
        ("newgame_tolerance", "ucinewgame"),
        ("idle_stop_tolerance", "stop"),
        ("unknown_command_tolerance", "nvcompact_unknown_command"),
    ] {
        checked(cases, label, "tcec4k", || {
            session.send(command)?;
            session.ready()?;
            Ok(json!({"command": command, "ready": true}))
        })?;
    }
    for (label, moves) in selected_cases(config) {
        let board = board_start(moves)?;
        let position = if moves.is_empty() {
            "position startpos".into()
        } else {
            format!("position startpos moves {moves}")
        };
        let go = format!(
            "go wtime {} btime {} winc {} binc {}",
            config.clock_ms, config.clock_ms, config.increment_ms, config.increment_ms
        );
        let full_clock = (config.clock_ms + config.clock_grace_ms) as f64 / 1000.0;
        let seconds = config.search_seconds.min(full_clock);
        let mut found = checked(cases, label, "tcec4k", || {
            search(session, &board, &position, &go, seconds, Some(full_clock))
        })?;
        found["case"] = json!(label);
        found["mode"] = json!("clock");
        found["budget"] = json!(config.clock_ms);
        observations.push(found);
    }
    checked(cases, "quit_idle", "tcec4k", || session.quit())?;
    Ok(())
}

fn extensions(
    session: &mut Session,
    config: &UciConfig,
    cases: &mut Vec<Value>,
    observations: &mut Vec<Value>,
    handshakes: &mut Vec<Value>,
) -> Result<()> {
    let h = checked(cases, "extension_handshake", "uci", || {
        handshake(session, config)
    })?;
    let _ = checked(cases, "uci_identification", "uci", || {
        if h["identity"]["name"].as_str().is_none_or(str::is_empty)
            || h["identity"]["author"].as_str().is_none_or(str::is_empty)
            || !h["option_errors"].as_array().unwrap().is_empty()
        {
            return Err(error(
                "protocol",
                "full UCI identification/options incomplete",
            ));
        }
        Ok(json!({"identity": h["identity"], "options_well_formed": true}))
    });
    handshakes.push(h);
    for (label, fen) in [
        (
            "fen_startpos",
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        ),
        ("fen_promotion", "8/P7/8/8/8/6k1/8/4K3 w - - 0 1"),
        ("fen_castling", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"),
        ("fen_en_passant", "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1"),
        ("fen_checkmate", "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"),
        ("fen_stalemate", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"),
    ] {
        let board = Board::from_fen(fen, false)
            .map_err(|e| anyhow::anyhow!("internal FEN corpus: {e:?}"))?;
        let mut found = checked(cases, label, "uci", || {
            search(
                session,
                &board,
                &format!("position fen {fen}"),
                &format!("go depth {}", config.depth),
                config.search_seconds,
                None,
            )
        })?;
        found["case"] = json!(label);
        found["mode"] = json!("depth");
        found["budget"] = json!(config.depth);
        observations.push(found);
    }
    for (mode, budget) in [
        ("depth", config.depth as u64),
        ("nodes", config.nodes),
        ("movetime", config.movetime_ms),
    ] {
        let engine_deadline = if mode == "movetime" {
            Some(budget.saturating_add(config.clock_grace_ms) as f64 / 1000.0)
        } else {
            None
        };
        let seconds = engine_deadline.map_or(config.search_seconds, |full| {
            config.search_seconds.min(full)
        });
        let mut found = checked(cases, &format!("go_{mode}"), "uci", || {
            search(
                session,
                &Board::default(),
                "position startpos",
                &format!("go {mode} {budget}"),
                seconds,
                engine_deadline,
            )
        })?;
        found["case"] = json!(format!("go_{mode}"));
        found["mode"] = json!(mode);
        found["budget"] = json!(budget);
        observations.push(found);
    }
    checked(cases, "ready_and_stop_during_infinite", "uci", || {
        session.send("position startpos")?;
        session.ready()?;
        session.send("go infinite")?;
        session.send("isready")?;
        session.wait_token("readyok", session.bound(config.stop_seconds))?;
        let started = Instant::now();
        session.send("stop")?;
        let mut answer = session.bestmove(&Board::default(), config.stop_seconds)?;
        answer["stop_to_bestmove_ms"] = json!(started.elapsed().as_secs_f64() * 1000.0);
        session.ready()?;
        Ok(answer)
    })?;
    checked(cases, "quit_during_search", "uci", || {
        session.send("position startpos")?;
        session.ready()?;
        session.send("go infinite")?;
        session.quit_state(true)
    })?;
    Ok(())
}

fn aggregate(cases: &[Value], requirement: &str) -> &'static str {
    let items: Vec<_> = cases
        .iter()
        .filter(|v| v["requirement"] == requirement)
        .collect();
    if items.iter().any(|v| v["status"] == "fail") {
        "fail"
    } else if items.iter().any(|v| v["status"] == "incomplete") {
        "incomplete"
    } else if items.is_empty() {
        "not_run"
    } else {
        "pass"
    }
}

fn leftovers(cwd: &Path) -> Result<Value> {
    let mut todo = vec![cwd.to_path_buf()];
    let mut paths = Vec::new();
    let mut truncated = false;
    while let Some(dir) = todo.pop() {
        for entry in fs::read_dir(&dir)? {
            let entry = entry?;
            let path = entry.path();
            if path != cwd.join("tmp") {
                paths.push(path.strip_prefix(cwd)?.to_string_lossy().into_owned());
            }
            if paths.len() >= 256 {
                truncated = true;
                break;
            }
            if entry.file_type()?.is_dir() {
                todo.push(path);
            }
        }
        if truncated {
            break;
        }
    }
    paths.sort();
    Ok(
        json!({"paths": paths, "truncated": truncated, "scope": "owned working directory, symlinks not followed"}),
    )
}

/// Run the actual complete artifact. Errors before launch stay errors; runtime
/// failures are returned as evidence rather than exceptions losing the transcript.
pub fn verify_engine(command: &[String], config: &UciConfig) -> Result<Value> {
    config.validate()?;
    if command.is_empty() || command.iter().any(|s| s.is_empty() || s.contains('\0')) {
        bail!("expected a nonempty argv array");
    }
    if !Path::new(&command[0]).is_absolute() {
        bail!("engine executable must be an absolute path; no implicit shell or PATH lookup");
    }
    let started = Instant::now();
    let deadline = started + Duration::from_secs_f64(config.max_seconds);
    let artifact_path = config.artifact_path.as_ref().map(PathBuf::from);
    let artifact_before = artifact_path.as_ref().map(fs::read).transpose()?;
    let artifact_resolved_before = artifact_path.as_ref().map(fs::canonicalize).transpose()?;
    let mut cases = Vec::new();
    let mut observations = Vec::new();
    let mut handshakes = Vec::new();
    let mut sessions = Vec::new();
    let temporary = tempfile::Builder::new()
        .prefix("nvcompact-uci-")
        .tempdir()?;
    let mut engine_started = false;
    for phase in ["core", "extensions"] {
        let requirement = if phase == "core" { "tcec4k" } else { "uci" };
        if phase == "extensions"
            && (!(config.extensions || config.profile == "uci")
                || aggregate(&cases, "tcec4k") != "pass")
        {
            continue;
        }
        let cwd = temporary.path().join(phase);
        fs::create_dir(&cwd)?;
        if Instant::now() >= deadline || process::cancelled() {
            cases.push(json!({"id": format!("{phase}_launch"), "requirement": requirement, "status": "incomplete", "kind": "budget", "error": "cancelled or budget exhausted before launch"}));
            break;
        }
        match Session::spawn(command, config, deadline, &cwd) {
            Ok(mut session) => {
                engine_started = true;
                let result = if phase == "core" {
                    core(
                        &mut session,
                        config,
                        &mut cases,
                        &mut observations,
                        &mut handshakes,
                    )
                } else {
                    extensions(
                        &mut session,
                        config,
                        &mut cases,
                        &mut observations,
                        &mut handshakes,
                    )
                };
                if let Err(err) = &result {
                    // Corpus/input failures outside a checked operation must not disappear.
                    if cases.last().is_none_or(|v| v["status"] == "pass") {
                        let (status, kind) = failure(err);
                        cases.push(json!({"id": format!("{phase}_internal"), "requirement": requirement, "status": status, "kind": kind, "error": err.to_string()}));
                    }
                }
                session.close();
                let files = leftovers(&cwd)?;
                if files["truncated"] == true || !files["paths"].as_array().unwrap().is_empty() {
                    let forced = session.cleanup["forced_cleanup"] == true;
                    cases.push(json!({"id": format!("{phase}_working_directory_cleanup"), "requirement": requirement,
                        "status": if forced { "incomplete" } else { "fail" }, "kind": "cleanup",
                        "harness_interrupted_cleanup": forced,
                        "error": if forced { "files observed after forced termination; engine cleanup may have been interrupted" } else { "engine left files in owned working directory" }, "files": files}));
                }
                sessions.push(session.summary(phase, files));
            }
            Err(err) => {
                let (status, kind) = failure(&err);
                cases.push(json!({"id": format!("{phase}_launch"), "requirement": requirement, "status": status, "kind": kind, "error": err.to_string()}));
            }
        }
    }
    let mut artifact = Value::Null;
    if let (Some(path), Some(before)) = (&artifact_path, &artifact_before) {
        artifact = json!({"path": path, "bytes": before.len(), "sha256": crate::sha256(before), "within_4096_bytes": before.len() <= 4096});
        if fs::read(path).ok().as_ref() != Some(before)
            || fs::canonicalize(path).ok() != artifact_resolved_before
        {
            cases.push(json!({"id": "artifact_unchanged", "requirement": "tcec4k", "status": "fail", "kind": "mutation", "error": "artifact bytes or symlink target changed"}));
        }
    }
    let core = aggregate(&cases, "tcec4k");
    let extended = aggregate(&cases, "uci");
    let requested_cases: Vec<_> = selected_cases(config)
        .into_iter()
        .map(|(name, _)| name)
        .collect();
    let completed_cases: Vec<_> = observations
        .iter()
        .filter_map(|v| v["case"].as_str())
        .filter(|name| START_CASES.iter().any(|(known, _)| known == name))
        .collect();
    let verdict = if config.profile == "tcec4k" {
        core
    } else if core == "fail" || extended == "fail" {
        "fail"
    } else if core == "pass" && extended == "pass" {
        "pass"
    } else {
        "incomplete"
    };
    Ok(
        json!({"format": FORMAT, "command": command, "configuration": config, "artifact": artifact,
        "profile": config.profile, "engine_started": engine_started, "cases": cases, "observations": observations,
        "handshakes": handshakes, "sessions": sessions, "verdict": verdict,
        "required_tcec4k_verdict": core, "extended_uci_verdict": extended,
        "core_case_coverage": {"corpus_cases": START_CASES.len(), "requested": requested_cases,
            "completed": completed_cases, "full_corpus_requested": requested_cases.len() == START_CASES.len(),
            "full_corpus_completed": completed_cases.len() == START_CASES.len()},
        "elapsed_ms": started.elapsed().as_secs_f64()*1000.0,
        "sources": [TCEC_SOURCE, "https://backscattering.de/chess/uci/"],
        "oracle": {"module": "cozy-chess", "development_only": true, "version_source": "Cargo.lock", "standard_castling_translation": true},
        "scope": {"evidence": "finite protocol and independent legal-move observations; not complete semantic equivalence, Elo, or organizer certification",
            "time_control": "configured short clock probes, not a 30min+3sec tournament unless separately run",
            "options": if config.preserve_engine_options { "original defaults and embedded constants preserved" } else { "explicit configured profile; original profile equivalence not claimed" },
            "cleanup": "owned cwd and original process group; no global filesystem or detached-session audit",
            "limits": "per-process AS/CPU/file limits, whole-verifier wall bound and per-session output bound; no aggregate memory cgroup"}}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn standard_castling_ep_promotion_and_terminal_moves() {
        for (_, moves) in START_CASES {
            board_start(moves).unwrap();
        }
        let board = Board::from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", false).unwrap();
        assert!(validate_bestmove("bestmove e1g1", &board).is_ok());
        assert!(validate_bestmove("bestmove e1c1", &board).is_ok());
        assert!(validate_bestmove("bestmove e1h1", &board).is_err());
        let ep = Board::from_fen("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", false).unwrap();
        assert!(validate_bestmove("bestmove e5d6", &ep).is_ok());
        let promoted = Board::from_fen("8/P7/8/8/8/6k1/8/4K3 w - - 0 1", false).unwrap();
        assert!(validate_bestmove("bestmove a7a8n", &promoted).is_ok());
        assert!(validate_bestmove("bestmove a7a8", &promoted).is_err());
        let mate = Board::from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", false).unwrap();
        assert!(validate_bestmove("bestmove 0000", &mate).is_ok());
        assert!(validate_bestmove("bestmove 0000", &Board::default()).is_err());
        assert!(validate_bestmove("bestmove e2e4 ponder e7e5", &Board::default()).is_ok());
        assert!(validate_bestmove("bestmove e2e4 ponder e2e3", &Board::default()).is_err());
    }

    #[test]
    fn options_are_parsed_and_invalid_ranges_rejected() {
        let parsed = parse_option("option name Hash type spin default 64 min 1 max 1024").unwrap();
        assert_eq!(parsed["default"], 64);
        assert!(parse_option("option name Hash type spin default 0 min 1 max 1024").is_err());
        assert!(parse_option("option name Ponder type check default maybe").is_err());
        assert!(
            parse_option("option name Style type combo default Solid var Solid var Risky").is_ok()
        );
    }

    fn fixture(script: &str, mut cfg: UciConfig) -> Value {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("engine.sh");
        fs::write(&file, script).unwrap();
        cfg.artifact_path = Some(file.to_string_lossy().into_owned());
        verify_engine(
            &["/bin/sh".into(), file.to_string_lossy().into_owned()],
            &cfg,
        )
        .unwrap()
    }

    const LEGAL: &str = "while IFS= read -r line; do\ncase \"$line\" in\nuci) printf 'option name Threads type spin default 17 min 1 max 128\\nuciok\\n';;\nisready) echo readyok;;\nposition*) case \"$line\" in\n'position startpos') move=e2e4;;\n*'g2h1q') move=b1c3;;\n*'e8g8') move=d1d2;;\n*'e5d6') move=c7d6;;\n*'e1g1') move=f8e7;;\n*) move=e7e5;;\nesac;;\ngo*) echo bestmove $move;;\nsetoption*) echo unexpected-setoption >&2; exit 7;;\nquit) exit 0;;\nesac\ndone\n";

    #[test]
    fn actual_six_case_protocol_preserves_options_and_cleans_up() {
        let cfg = UciConfig {
            max_seconds: 5.0,
            cleanup_seconds: 0.2,
            ..UciConfig::default()
        };
        let result = fixture(LEGAL, cfg);
        assert_eq!(result["verdict"], "pass", "{result:#}");
        assert_eq!(result["observations"].as_array().unwrap().len(), 6);
        assert!(result["sessions"][0]["transcript"]
            .as_array()
            .unwrap()
            .iter()
            .all(|v| !v["text"].as_str().unwrap().starts_with("setoption")));
        assert_eq!(result["sessions"][0]["cleanup"]["forced_cleanup"], false);
    }

    #[test]
    fn illegal_duplicate_timeout_and_leftover_are_not_passes() {
        let cfg = UciConfig {
            quick: true,
            startup_seconds: 0.2,
            ready_seconds: 0.2,
            search_seconds: 0.2,
            max_seconds: 2.0,
            cleanup_seconds: 0.1,
            ..UciConfig::default()
        };
        for script in [
            LEGAL.replace("echo bestmove $move", "echo bestmove a1a8"),
            LEGAL.replace(
                "echo bestmove $move",
                "printf 'bestmove %s\\nbestmove %s\\n' $move $move",
            ),
            "while :; do sleep 1; done".into(),
            LEGAL.replace("quit) exit 0", "quit) echo x > left; exit 0"),
        ] {
            let result = fixture(&script, cfg.clone());
            assert_ne!(result["verdict"], "pass", "{result:#}");
        }
    }

    #[test]
    fn output_flood_is_bounded_without_reader_threads() {
        let result = fixture(
            "yes x",
            UciConfig {
                max_output_bytes: 4096,
                max_seconds: 2.0,
                startup_seconds: 1.0,
                cleanup_seconds: 0.1,
                ..UciConfig::default()
            },
        );
        assert_eq!(result["verdict"], "fail");
        assert_eq!(result["cases"][0]["kind"], "output_limit");
        assert!(result["elapsed_ms"].as_f64().unwrap() < 2000.0);
    }

    #[test]
    fn observation_timeout_before_clock_expiry_is_incomplete() {
        let delayed = LEGAL.replace("echo bestmove $move", "sleep 1; echo bestmove $move");
        let config = UciConfig {
            case_ids: vec!["startpos_white".into()],
            clock_ms: 5000,
            clock_grace_ms: 0,
            search_seconds: 0.05,
            max_seconds: 2.0,
            cleanup_seconds: 0.1,
            ..UciConfig::default()
        };
        let observation = fixture(&delayed, config.clone());
        assert_eq!(observation["verdict"], "incomplete", "{observation:#}");
        assert_eq!(observation["cases"][4]["kind"], "probe_budget");
        let actual_clock = fixture(
            &delayed,
            UciConfig {
                clock_ms: 20,
                search_seconds: 1.0,
                ..config
            },
        );
        assert_eq!(actual_clock["verdict"], "fail", "{actual_clock:#}");
        assert_eq!(actual_clock["cases"][4]["kind"], "timeout");
    }

    #[test]
    fn requested_case_subset_is_validated_and_reported_as_partial_coverage() {
        let config = UciConfig {
            case_ids: vec!["en_passant_history".into()],
            max_seconds: 2.0,
            cleanup_seconds: 0.1,
            ..UciConfig::default()
        };
        let result = fixture(LEGAL, config.clone());
        assert_eq!(result["verdict"], "pass", "{result:#}");
        assert_eq!(
            result["core_case_coverage"]["requested"],
            json!(["en_passant_history"])
        );
        assert_eq!(
            result["core_case_coverage"]["completed"],
            json!(["en_passant_history"])
        );
        assert_eq!(result["core_case_coverage"]["full_corpus_completed"], false);
        assert!(UciConfig {
            quick: true,
            ..config.clone()
        }
        .validate()
        .is_err());
        assert!(UciConfig {
            case_ids: vec!["invented-case".into()],
            ..config
        }
        .validate()
        .is_err());
    }
}
