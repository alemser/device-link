package com.alemser.amplink.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Badge
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import com.alemser.amplink.core.BridgeClient
import com.alemser.amplink.core.DEVICELINK_API
import com.alemser.amplink.core.FoundBridge
import com.alemser.amplink.core.KnownDevices
import com.alemser.amplink.core.ListedDevice
import com.alemser.amplink.core.LocalNetwork
import com.alemser.amplink.core.discover
import kotlinx.coroutines.delay

/** Chosen: often enough that a device switched on shows up while the person looks (docs/contract-v2.md). */
private const val ROUND_MS = 5_000L

/**
 * Every device on the Wi-Fi. Discovery repeats every [ROUND_MS] while this screen is on show, and stops when the app
 * goes to the background or a device is opened (docs/contract-v2.md, "For the app").
 */
@Composable
fun DevicesScreen(
    local: LocalNetwork,
    known: KnownDevices,
    onOpen: (ListedDevice) -> Unit,
    onSetup: () -> Unit,
) {
    var devices by remember { mutableStateOf(known.list()) }
    var searching by remember { mutableStateOf(true) }
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    LaunchedEffect(lifecycle) {
        lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                searching = true
                val found = runCatching { discover(open = local::wifiSocket) }.getOrDefault(emptyList())
                devices = known.update(found.map { withLabel(it, known) })
                searching = false
                delay(ROUND_MS)
            }
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("DeviceLink", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.padding(top = 16.dp))
        LinearProgressIndicator(Modifier.fillMaxWidth().alpha(if (searching) 1f else 0f))
        if (devices.isEmpty()) {
            Text("Looking for devices on this Wi-Fi")
            Hint("The phone must be on the same Wi-Fi as the devices. A device that isn't on the Wi-Fi yet opens its own setup network.")
        }
        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(devices, key = { it.bridge.name }) { device -> DeviceRow(device) { onOpen(device) } }
        }
        OutlinedButton(onClick = onSetup, Modifier.fillMaxWidth().padding(bottom = 16.dp)) {
            Text("Set up a new device's Wi-Fi")
        }
    }
}

/**
 * An api 1 bridge's discovery answer has no label or kind (today's SP103): api 1 is the amplifier contract, so the kind
 * is "amplifier", and the label is the model from its `/device`, asked once and then remembered with the device.
 */
private suspend fun withLabel(bridge: FoundBridge, known: KnownDevices): FoundBridge {
    if (bridge.label.isNotEmpty()) return bridge
    val kind = bridge.kind.ifEmpty { if (bridge.api < DEVICELINK_API) "amplifier" else "" }
    val label = known.get(bridge.name)?.label?.takeIf { it.isNotEmpty() }
        ?: runCatching { BridgeClient(bridge.ip).device().model }.getOrDefault("")
    return bridge.copy(label = label, kind = kind)
}

@Composable
private fun DeviceRow(device: ListedDevice, onClick: () -> Unit) {
    val bridge = device.bridge
    Surface(
        shape = RoundedCornerShape(14.dp),
        color = MaterialTheme.colorScheme.surfaceContainer,
        modifier = Modifier
            .fillMaxWidth()
            .alpha(if (device.online) 1f else 0.45f)
            .clickable(enabled = device.online, onClick = onClick),
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(kindIcon(bridge.kind), contentDescription = null, Modifier.size(32.dp))
            Column(Modifier.weight(1f).padding(start = 14.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(bridge.title, style = MaterialTheme.typography.titleMedium)
                    if (device.new) Badge(Modifier.padding(start = 8.dp)) { Text("new") }
                }
                Hint(
                    if (device.online) "${kindLabel(bridge.kind)}  ·  ${bridge.ip}" else "${kindLabel(bridge.kind)}  ·  offline",
                )
            }
        }
    }
}
