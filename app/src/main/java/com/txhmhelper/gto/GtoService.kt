package com.txhmhelper.gto

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface GtoService {
    @GET("health")
    suspend fun health(): Map<String, String>

    @POST("solve")
    suspend fun solve(@Body request: GtoSolveRequest): GtoSolveResponse
}
