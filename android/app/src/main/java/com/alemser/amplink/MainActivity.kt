package com.alemser.amplink

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.GraphicEq
import androidx.compose.material.icons.outlined.MonitorHeart
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Tv
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.edit
import com.alemser.amplink.core.BridgeClient
import com.alemser.amplink.core.ConfigStore
import com.alemser.amplink.core.DEVICELINK_API
import com.alemser.amplink.core.Device
import com.alemser.amplink.core.FoundBridge
import com.alemser.amplink.core.KnownDevices
import com.alemser.amplink.core.LocalNetwork
import com.alemser.amplink.core.SUPPORTED_API
import com.alemser.amplink.core.WifiSetupClient
import com.alemser.amplink.core.discover
import com.alemser.amplink.core.isIpv4
import com.alemser.amplink.ui.AmpLinkTheme
import com.alemser.amplink.ui.DeviceScreen
import com.alemser.amplink.ui.DevicesScreen
import com.alemser.amplink.ui.DiagnosticsScreen
import com.alemser.amplink.ui.DisplayScreen
import com.alemser.amplink.ui.Hint
import com.alemser.amplink.ui.IpField
import com.alemser.amplink.ui.NamesScreen
import com.alemser.amplink.ui.NowScreen
import com.alemser.amplink.ui.WifiSetupScreen
import kotlinx.coroutines.launch
import java.io.IOException

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

/**
 * DeviceLink (docs/contract-v2.md): every device on the Wi-Fi in one list; an api 2 device opens the screen built from
 * its description, an api 1 amplifier the amplifier tabs.
 */
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
            if (s.bridge.api >= DEVICELINK_API) {
                DeviceScreen(client, s.bridge.title, onBack = { screen = Screen.List })
            } else {
                AmpScreen(client, onBack = { screen = Screen.List }, onSetup = { screen = Screen.Setup })
            }
        }
    }
}

/** An api 1 amplifier: its description, then today's tabs. */
@Composable
private fun AmpScreen(client: BridgeClient, onBack: () -> Unit, onSetup: () -> Unit) {
    BackHandler(onBack = onBack)
    var device by remember(client) { mutableStateOf<Device?>(null) }
    var error by remember(client) { mutableStateOf<String?>(null) }
    LaunchedEffect(client) {
        try {
            device = client.device()
        } catch (e: IOException) {
            error = e.message ?: "Couldn't reach the bridge"
        }
    }
    val found = device
    if (found != null) {
        Tabs(client, found, onBack = onBack, onSetup = onSetup)
    } else {
        Column(
            Modifier
                .fillMaxSize()
                .safeDrawingPadding()
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (error == null) CircularProgressIndicator() else Text("Couldn't open the amp: $error")
            TextButton(onClick = onBack) { Text("Back to the devices") }
        }
    }
}

private enum class Tab(val label: String, val icon: ImageVector) {
    NOW("Now", Icons.Outlined.GraphicEq),
    DISPLAY("Display", Icons.Outlined.Tv),
    NAMES("Names", Icons.Outlined.Edit),
    DIAGNOSTICS("Status", Icons.Outlined.MonitorHeart),
}

private fun tabsOf(device: Device): List<Tab> = buildList {
    add(Tab.NOW)
    if (device.has("config")) {
        if (device.has("vu") || device.has("info_screens")) add(Tab.DISPLAY)
        add(Tab.NAMES)
    }
    add(Tab.DIAGNOSTICS)
}

/** Only the open tab is composed, so a section asks the bridge for nothing until it's opened. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun Tabs(client: BridgeClient, device: Device, onBack: () -> Unit, onSetup: () -> Unit) {
    val tabs = remember(device) { tabsOf(device) }
    var selected by rememberSaveable { mutableStateOf(Tab.NOW) }
    var settings by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val store = remember(client) { ConfigStore(client, scope) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(device.model, maxLines = 1) },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = "Devices") }
                },
                actions = {
                    if (device.has("wifi_setup")) {
                        IconButton(onClick = { settings = true }) {
                            Icon(Icons.Outlined.Settings, contentDescription = "Bridge")
                        }
                    }
                },
            )
        },
        bottomBar = {
            NavigationBar {
                tabs.forEach { tab ->
                    NavigationBarItem(
                        selected = selected == tab,
                        onClick = { selected = tab },
                        icon = { Icon(tab.icon, contentDescription = null) },
                        label = { Text(tab.label, maxLines = 1) },
                    )
                }
            }
        },
    ) { padding ->
        val page = Modifier
            .padding(padding)
            .consumeWindowInsets(padding)
        when (selected) {
            Tab.NOW -> NowScreen(client, device, page)
            Tab.DISPLAY -> DisplayScreen(store, device, page)
            Tab.NAMES -> NamesScreen(store, device, page)
            Tab.DIAGNOSTICS -> DiagnosticsScreen(client, device, page)
        }
    }

    if (settings) {
        var wifiError by remember { mutableStateOf<String?>(null) }
        AlertDialog(
            onDismissRequest = { settings = false },
            title = { Text("Bridge") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Hint("At ${client.host}")
                    TextButton(onClick = {
                        // The bridge opens its setup network for 10 minutes, without leaving this one.
                        scope.launch {
                            try {
                                WifiSetupClient(client.host).openSetup()
                                settings = false
                                onSetup()
                            } catch (e: IOException) {
                                wifiError = e.message ?: "Couldn't reach the bridge"
                            }
                        }
                    }) { Text("Change the amp's Wi-Fi") }
                    wifiError?.let { Hint(it, MaterialTheme.colorScheme.error) }
                }
            },
            confirmButton = { TextButton(onClick = { settings = false }) { Text("Close") } },
        )
    }
}
