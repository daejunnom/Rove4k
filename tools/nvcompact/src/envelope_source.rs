//! Source-search strategies share one evaluator but retain independent cost
//! contexts and evidence. A submitted-codec winner stays in the final portfolio
//! even when a different codec objective chooses a different source.
use crate::{codec::Recipe, envelope_cost::WholeFileObjective, sha256, source_search};
use anyhow::{ensure, Context, Result};
use serde_json::{json, Value};
use std::{fs, path::Path};

pub(crate) struct SourceCandidate {
    pub id: String,
    pub data: Vec<u8>,
    pub summary: Value,
}

struct CostView<'a> {
    objective: &'a mut WholeFileObjective,
    fixed: Option<&'a Recipe>,
}

impl source_search::CompleteFileObjective for CostView<'_> {
    fn measure(&mut self, data: &[u8]) -> Result<usize> {
        match self.fixed {
            Some(recipe) => self.objective.measure_recipe(data, recipe),
            None => self.objective.measure(data),
        }
    }
    fn fresh_measure(&mut self, data: &[u8]) -> Result<usize> {
        match self.fixed {
            Some(recipe) => self.objective.fresh_measure_recipe(data, recipe),
            None => self.objective.fresh_measure(data),
        }
    }
}

pub(crate) fn search(
    payload: &[u8],
    options: &source_search::SourceSearchOptions,
    compiler: &[String],
    objective: &mut WholeFileObjective,
    submitted: &Recipe,
    output: &Path,
    fixed_context: Value,
    implementation: &Value,
    portfolio_search: bool,
) -> Result<Vec<SourceCandidate>> {
    let mut candidates = Vec::new();
    let mut portfolio_context = objective.context();
    portfolio_context["implementation"] = implementation.clone();
    // Priority is part of the declared strategy portfolio. It preserves the
    // old objective's seed without mixing its costs into another archive.
    for (name, fixed, context) in [
        ("source-search", Some(submitted), fixed_context),
        ("source-search-portfolio", None, portfolio_context),
    ] {
        if fixed.is_none() && !portfolio_search {
            continue;
        }
        let mut view = CostView { objective, fixed };
        let searched = source_search::search_with_objective(
            payload,
            options,
            compiler,
            &output.join(name),
            Some(&context),
            &mut view,
        )?;
        let id = format!("c-source-search-{}", &sha256(&searched.data)[..16]);
        let report_path = format!("{name}/source-search/report.json");
        let report_bytes = fs::read(output.join(&report_path))?;
        let mut report = searched.report;
        let records = report["records"].as_array().map_or(0, Vec::len);
        report
            .as_object_mut()
            .context("source-search report is not an object")?
            .remove("records");
        report["detail"] = json!({"path":report_path,"sha256":sha256(&report_bytes),
            "bytes":report_bytes.len(),"records":records});
        ensure!(
            searched.recipe["final"]["payload_sha256"] == sha256(&searched.data),
            "source-search output differs from its recorded recipe"
        );
        candidates.push(SourceCandidate { id: id.clone(), data: searched.data,
            summary: json!({"strategy":name,"variant":id,"report":report,"recipe":searched.recipe,
                "cost_codec":fixed,"cost_objective":context,
                "cost_scope":"complete inspected header plus encoded whole payload",
                "budget_scope":"this strategy has its own declared search limits; final codec comparison retains every strategy winner"}) });
    }
    Ok(candidates)
}
