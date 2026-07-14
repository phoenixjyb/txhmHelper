package com.txhmhelper.gto

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.POST

interface GtoService {
    @GET("health")
    suspend fun health(): Map<String, String>

    @POST("solve")
    suspend fun solve(@Body request: GtoSolveRequest): GtoSolveResponse

    @POST("v1/table/solve")
    suspend fun createTableSolve(@Body request: GtoTableSolveRequest): GtoSolveJobResponse

    @GET("v1/solve/{jobId}")
    suspend fun getSolveJob(@Path("jobId") jobId: String): GtoSolveJobResponse
}
