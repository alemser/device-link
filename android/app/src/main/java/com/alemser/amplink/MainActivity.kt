package com.alemser.amplink

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
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
import androidx.compose.material.icons.Icons
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
import com.alemser.amplink.core.Device
import com.alemser.amplink.core.SUPPORTED_API
import com.alemser.amplink.core.isIpv4
import com.alemser.amplink.ui.AmpLinkTheme
import com.alemser.amplink.ui.DiagnosticsScreen
import com.alemser.amplink.ui.DisplayScreen
import com.alemser.amplink.ui.Hint
import com.alemser.amplink.ui.IpField
import com.alemser.amplink.ui.NamesScreen
import com.alemser.amplink.ui.NowScreen
import java.io.IOException

private const val PREFS = "amp-link"
private const val KEY_HOST = "host"
private const val DEFAULT_HOST = "192.168.178.108"

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

@Composable
private fun Root() {
    val prefs = LocalContext.current.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    var host by rememberSaveable { mutableStateOf(prefs.getString(KEY_HOST, null) ?: DEFAULT_HOST) }
    var attempt by remember { mutableIntStateOf(0) }
    val client = remember(host) { BridgeClient(host) }
    var device by remember(client) { mutableStateOf<Device?>(null) }
    var error by remember(client) { mutableStateOf<String?>(null) }

    fun connectTo(address: String) {
        prefs.edit { putString(KEY_HOST, address) }
        host = address
        attempt++
    }

    // /device doesn't change while the bridge runs: one read per connection.
    LaunchedEffect(client, attempt) {
        if (device != null) return@LaunchedEffect
        error = null
        try {
            val found = client.device()
            if (found.api == SUPPORTED_API) {
                device = found
            } else {
                error = "This bridge speaks API ${found.api}, and this app speaks $SUPPORTED_API"
            }
        } catch (e: IOException) {
            error = e.message ?: "Couldn't reach the bridge"
        }
    }

    val found = device
    if (found == null) {
        ConnectScreen(host, error, onConnect = ::connectTo)
    } else {
        Tabs(client, found, onHost = ::connectTo)
    }
}

@Composable
private fun ConnectScreen(host: String, error: String?, onConnect: (String) -> Unit) {
    var address by remember(host) { mutableStateOf(host) }
    Column(
        Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .imePadding()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("Amp Link", style = MaterialTheme.typography.headlineMedium)
        if (error == null) {
            CircularProgressIndicator()
            Hint("Looking for the bridge at $host")
        } else {
            Text("Couldn't connect: $error", color = MaterialTheme.colorScheme.error)
            Hint("The phone must be on the same Wi-Fi as the amp")
            IpField("Bridge address (IP)", address, !isIpv4(address)) { address = it }
            Button(
                onClick = { onConnect(address) },
                enabled = isIpv4(address),
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Connect") }
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
private fun Tabs(client: BridgeClient, device: Device, onHost: (String) -> Unit) {
    val tabs = remember(device) { tabsOf(device) }
    var selected by rememberSaveable { mutableStateOf(Tab.NOW) }
    var editingHost by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val store = remember(client) { ConfigStore(client, scope) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(device.model, maxLines = 1) },
                actions = {
                    IconButton(onClick = { editingHost = true }) {
                        Icon(Icons.Outlined.Settings, contentDescription = "Bridge address")
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

    if (editingHost) {
        var address by remember { mutableStateOf(client.host) }
        AlertDialog(
            onDismissRequest = { editingHost = false },
            title = { Text("Bridge address") },
            text = { IpField("IP", address, !isIpv4(address)) { address = it } },
            confirmButton = {
                TextButton(
                    onClick = {
                        editingHost = false
                        onHost(address)
                    },
                    enabled = isIpv4(address),
                ) { Text("Connect") }
            },
            dismissButton = { TextButton(onClick = { editingHost = false }) { Text("Cancel") } },
        )
    }
}
