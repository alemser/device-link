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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import com.alemser.amplink.core.Device
import com.alemser.amplink.core.FoundBridge
import com.alemser.amplink.core.LocalNetwork
import com.alemser.amplink.core.SUPPORTED_API
import com.alemser.amplink.core.WifiSetupClient
import com.alemser.amplink.core.discover
import com.alemser.amplink.core.isIpv4
import com.alemser.amplink.ui.AmpLinkTheme
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
private const val KEY_HOST = "host"

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

/** Where finding the bridge stands, before the tabs. */
private sealed interface Finding {
    data class Trying(val host: String) : Finding
    data object Searching : Finding

    /** The saved address didn't answer (or there's none), and the search gave this. */
    data class Result(val error: String?, val found: List<FoundBridge>) : Finding
}

@Composable
private fun Root() {
    val context = LocalContext.current
    val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    val local = remember { LocalNetwork(context.applicationContext) }
    var host by rememberSaveable { mutableStateOf(prefs.getString(KEY_HOST, null)) }
    var attempt by remember { mutableIntStateOf(0) }
    var settingUp by rememberSaveable { mutableStateOf(false) }
    val client = remember(host) { host?.let(::BridgeClient) }
    var device by remember(client) { mutableStateOf<Device?>(null) }
    var finding by remember(client) { mutableStateOf<Finding>(Finding.Searching) }

    fun connectTo(address: String) {
        prefs.edit { putString(KEY_HOST, address) }
        host = address
        attempt++
    }

    // The saved address first; if it doesn't answer (the router gave the bridge another IP, or it's the first
    // run), the bridges on the network answer the discovery broadcast. One of them: connect to it at once.
    LaunchedEffect(client, attempt) {
        if (device != null || settingUp) return@LaunchedEffect
        var error: String? = null
        if (client != null) {
            finding = Finding.Trying(client.host)
            try {
                val found = client.device()
                if (found.api == SUPPORTED_API) {
                    device = found
                    return@LaunchedEffect
                }
                error = "This bridge speaks API ${found.api}, and this app speaks $SUPPORTED_API"
            } catch (e: IOException) {
                error = e.message ?: "Couldn't reach the bridge"
            }
        }
        finding = Finding.Searching
        val found = runCatching { discover(open = local::wifiSocket) }.getOrDefault(emptyList())
        val other = found.singleOrNull()
        if (other != null && other.ip != client?.host) {
            connectTo(other.ip)
        } else {
            finding = Finding.Result(error, found)
        }
    }

    val found = device
    when {
        settingUp -> WifiSetupScreen(
            local,
            onDone = {
                settingUp = false
                connectTo(it)
            },
            onCancel = {
                settingUp = false
                attempt++
            },
        )
        found == null || client == null -> ConnectScreen(
            finding,
            host.orEmpty(),
            onConnect = ::connectTo,
            onSearch = { attempt++ },
            onSetup = { settingUp = true },
        )
        else -> Tabs(
            client,
            found,
            onHost = ::connectTo,
            onSearch = {
                prefs.edit { remove(KEY_HOST) }
                host = null
                attempt++
            },
            onSetup = { settingUp = true },
        )
    }
}

@Composable
private fun ConnectScreen(
    finding: Finding,
    host: String,
    onConnect: (String) -> Unit,
    onSearch: () -> Unit,
    onSetup: () -> Unit,
) {
    var address by remember(host) { mutableStateOf(host) }
    var typing by remember { mutableStateOf(false) }
    Column(
        Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .imePadding()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("Amp Link", style = MaterialTheme.typography.headlineMedium)
        when (finding) {
            is Finding.Trying -> {
                CircularProgressIndicator()
                Hint("Looking for the bridge at ${finding.host}")
            }
            Finding.Searching -> {
                CircularProgressIndicator()
                Hint("Looking for bridges on this Wi-Fi")
            }
            is Finding.Result -> {
                finding.error?.let { Text("Couldn't connect to $host: $it", color = MaterialTheme.colorScheme.error) }
                if (finding.found.isEmpty()) {
                    Text("No bridge answered on this Wi-Fi")
                    Hint("The phone must be on the same Wi-Fi as the amp. An amp that isn't on the Wi-Fi yet opens its own setup network.")
                } else {
                    Text("Bridges on this Wi-Fi")
                    finding.found.forEach { bridge ->
                        OutlinedButton(onClick = { onConnect(bridge.ip) }, Modifier.fillMaxWidth()) {
                            Text("${bridge.name}  ·  ${bridge.ip}")
                        }
                    }
                }
                Button(onClick = onSearch, Modifier.fillMaxWidth()) { Text("Search again") }
                OutlinedButton(onClick = onSetup, Modifier.fillMaxWidth()) { Text("Set up the amp's Wi-Fi") }
                if (typing) {
                    IpField("Bridge address (IP)", address, !isIpv4(address)) { address = it }
                    Button(
                        onClick = { onConnect(address) },
                        enabled = isIpv4(address),
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Connect") }
                } else {
                    TextButton(onClick = { typing = true }) { Text("Type the address") }
                }
            }
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
private fun Tabs(
    client: BridgeClient,
    device: Device,
    onHost: (String) -> Unit,
    onSearch: () -> Unit,
    onSetup: () -> Unit,
) {
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
                        Icon(Icons.Outlined.Settings, contentDescription = "Bridge")
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
        var wifiError by remember { mutableStateOf<String?>(null) }
        AlertDialog(
            onDismissRequest = { editingHost = false },
            title = { Text("Bridge") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    IpField("Address (IP)", address, !isIpv4(address)) { address = it }
                    TextButton(onClick = {
                        editingHost = false
                        onSearch()
                    }) { Text("Search the Wi-Fi again") }
                    if (device.has("wifi_setup")) {
                        TextButton(onClick = {
                            // The bridge opens its setup network for 10 minutes, without leaving this one.
                            scope.launch {
                                try {
                                    WifiSetupClient(client.host).openSetup()
                                    editingHost = false
                                    onSetup()
                                } catch (e: IOException) {
                                    wifiError = e.message ?: "Couldn't reach the bridge"
                                }
                            }
                        }) { Text("Change the amp's Wi-Fi") }
                        wifiError?.let { Hint(it, MaterialTheme.colorScheme.error) }
                    }
                }
            },
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
