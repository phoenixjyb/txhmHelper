package com.txhmhelper.gto

import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import com.txhmhelper.model.Stage
import org.junit.Assert.assertTrue
import org.junit.Test

class GtoModelsTest {
    @Test
    fun solveRequestUsesBackendFieldNames() {
        val request = GtoSolveRequest(
            stage = Stage.FLOP,
            hole = listOf("As", "Kd"),
            board = listOf("Jh", "Td", "2c"),
            pot = 10.0,
            effectiveStack = 100.0,
            betSizing = listOf(0.33, 0.5)
        )
        val json = Moshi.Builder()
            .add(KotlinJsonAdapterFactory())
            .build()
            .adapter(GtoSolveRequest::class.java)
            .toJson(request)

        assertTrue(json.contains("\"effective_stack\":100.0"))
        assertTrue(json.contains("\"bet_sizing\":[0.33,0.5]"))
    }
}
