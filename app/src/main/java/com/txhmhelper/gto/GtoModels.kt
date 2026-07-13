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
