package com.txhmhelper.gto

import com.squareup.moshi.Moshi
import com.txhmhelper.BuildConfig
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

object GtoClient {
    private val moshi: Moshi = Moshi.Builder().build()

    private val okHttp = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(5, TimeUnit.SECONDS)
        .build()

    val service: GtoService by lazy {
        Retrofit.Builder()
            .baseUrl(BuildConfig.GTO_BASE_URL)
            .client(okHttp)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
            .create(GtoService::class.java)
    }
}
