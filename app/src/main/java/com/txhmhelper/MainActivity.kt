package com.txhmhelper

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.txhmhelper.ui.HandOddsScreen
import com.txhmhelper.ui.theme.TxhmHelperTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            TxhmHelperTheme {
                HandOddsScreen()
            }
        }
    }
}
