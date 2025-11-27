package com.txhmhelper.gto

import com.txhmhelper.model.Stage

data class GtoSolveRequest(
    val stage: Stage,
    val hole: List<String>,
    val board: List<String>,
    val pot: Double,
    val effectiveStack: Double,
    val betSizing: List<Double> = listOf(0.33, 0.5, 1.0)
)

data class GtoSolveResponse(
    val strategy: Map<String, Double>,
    val note: String
)
