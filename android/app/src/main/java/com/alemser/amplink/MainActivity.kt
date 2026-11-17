package com.alemser.amplink

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import com.alemser.amplink.core.BridgeClient
import com.alemser.amplink.core.FoundBridge
import com.alemser.amplink.core.KnownDevices
import com.alemser.amplink.core.LocalNetwork
import com.alemser.amplink.ui.AmpLinkTheme
import com.alemser.amplink.ui.DeviceScreen
import com.alemser.amplink.ui.DevicesScreen
import com.alemser.amplink.ui.WifiSetupScreen

private const val PREFS = "amp-link"

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            AmpLinkTheme {
                Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) { Root() }
            }
        }
    }
}

/** What's on screen: the device list, one device, or a new device's Wi-Fi setup. */
private sealed interface Screen {
    data object List : Screen
    data class Open(val bridge: FoundBridge) : Screen
    data object Setup : Screen
}

/** DeviceLink (docs/contract-v2.md): every device on the Wi-Fi in one list; each opens the screen built from its description. */
@Composable
private fun Root() {
    val context = LocalContext.current
    val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    val local = remember { LocalNetwork(context.applicationContext) }
    val known = remember { KnownDevices(prefs) }
    var screen by remember { mutableStateOf<Screen>(Screen.List) }

    when (val s = screen) {
        Screen.List -> DevicesScreen(
            local,
            known,
            onOpen = {
                known.seen(it.bridge.name)
                screen = Screen.Open(it.bridge)
            },
            onSetup = { screen = Screen.Setup },
        )
        Screen.Setup -> WifiSetupScreen(local, onDone = { screen = Screen.List }, onCancel = { screen = Screen.List })
        is Screen.Open -> {
            val client = remember(s.bridge.ip) { BridgeClient(s.bridge.ip) }
            DeviceScreen(client, s.bridge.title, onBack = { screen = Screen.List }, onSetup = { screen = Screen.Setup })
        }
    }
}
