package com.txhmhelper.gto

import com.txhmhelper.model.Stage
import com.squareup.moshi.Json

data class GtoSolveRequest(
    val stage: Stage,
    val hole: List<String>,
    val board: List<String>,
    val pot: Double,
    @Json(name = "effective_stack")
    val effectiveStack: Double,
    @Json(name = "bet_sizing")
    val betSizing: List<Double> = listOf(0.33, 0.5, 1.0)
)

data class GtoSolveResponse(
    val strategy: Map<String, Double>,
    val note: String
)

data class GtoTableAction(
    val player: String,
    val type: String,
    @Json(name = "amount_to")
    val amountTo: Double? = null
)

data class GtoTableSolveRequest(
    val stage: String,
    val hole: List<String>,
    val board: List<String>,
    @Json(name = "pot_before_street")
    val potBeforeStreet: Double,
    @Json(name = "effective_stack")
    val effectiveStack: Double,
    @Json(name = "hero_position")
    val heroPosition: String,
    val actions: List<GtoTableAction>,
    val iterations: Int = 3_000,
    @Json(name = "terminal_evaluator")
    val terminalEvaluator: String = "cuda"
)

data class GtoV1SolveResult(
    val strategy: Map<String, Double>,
    val iterations: Int,
    @Json(name = "node_count")
    val nodeCount: Int,
    val model: String,
    @Json(name = "terminal_evaluator")
    val terminalEvaluator: String,
    @Json(name = "action_history")
    val actionHistory: List<String> = emptyList(),
    val note: String
)

data class GtoSolveJobResponse(
    @Json(name = "job_id")
    val jobId: String,
    val status: String,
    @Json(name = "cache_hit")
    val cacheHit: Boolean = false,
    val result: GtoV1SolveResult? = null,
    val error: String? = null
)
