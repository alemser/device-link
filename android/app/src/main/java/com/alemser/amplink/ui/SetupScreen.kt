package com.alemser.amplink.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material.icons.outlined.VisibilityOff
import androidx.compose.material.icons.outlined.Wifi
import androidx.compose.material3.IconButton
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.alemser.amplink.core.BridgeClient
import com.alemser.amplink.core.LocalNetwork
import com.alemser.amplink.core.SETUP_HOST
import com.alemser.amplink.core.SETUP_KEY
import com.alemser.amplink.core.SETUP_PREFIX
import com.alemser.amplink.core.WifiNetwork
import com.alemser.amplink.core.WifiSetupClient
import com.alemser.amplink.core.bridgeName
import com.alemser.amplink.core.discover
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.IOException

private sealed interface Step {
    data object Joining : Step
    data class Picking(val networks: List<WifiNetwork>, val note: String? = null) : Step
    data class Password(val network: WifiNetwork) : Step
    data class Waiting(val text: String) : Step
    data class Failed(val why: String) : Step
}

/**
 * Sets up a bridge's Wi-Fi: joins its setup network (Android asks), lists the networks the bridge sees, sends the
 * chosen one, then gives the setup network back and finds the bridge on the home network. [onDone] gets its IP.
 */
@Composable
fun WifiSetupScreen(local: LocalNetwork, onDone: (String) -> Unit, onCancel: () -> Unit) {
    var step by remember { mutableStateOf<Step>(Step.Joining) }
    var client by remember { mutableStateOf<WifiSetupClient?>(null) }
    var name by remember { mutableStateOf("") }
    var attempt by remember { mutableIntStateOf(0) }
    val scope = rememberCoroutineScope()

    DisposableEffect(Unit) { onDispose { local.leaveSetup() } }

    LaunchedEffect(attempt) {
        if (!local.canJoinSetup) {
            step = Step.Failed(
                "This phone joins the amp's network only from Android 10. In the Wi-Fi settings, join the network " +
                    "starting with $SETUP_PREFIX (password $SETUP_KEY) and open http://$SETUP_HOST/ in the browser.",
            )
            return@LaunchedEffect
        }
        step = Step.Joining
        try {
            val (http, ssid) = local.joinSetup()
            val setup = WifiSetupClient(SETUP_HOST, http)
            client = setup
            name = bridgeName(ssid.ifEmpty { runCatching { setup.status().setup.ssid }.getOrDefault("") })
            step = Step.Picking(setup.networks())
        } catch (e: IOException) {
            local.leaveSetup()
            step = Step.Failed(e.message ?: "Couldn't reach the amp's setup network")
        }
    }

    fun send(network: WifiNetwork, psk: String) {
        val setup = client ?: return
        scope.launch {
            step = Step.Waiting("Joining ${network.ssid}…")
            val outcome = try {
                setup.join(network.ssid, psk)
                setup.awaitOutcome()
            } catch (e: IOException) {
                step = Step.Picking(runCatching { setup.networks() }.getOrDefault(emptyList()), e.message)
                return@launch
            }
            if (outcome.state != "connected" || outcome.ip.isEmpty()) {
                step = Step.Picking(
                    runCatching { setup.networks() }.getOrDefault(emptyList()),
                    "Didn't join ${network.ssid}: ${outcome.detail}",
                )
                return@launch
            }
            step = Step.Waiting("Joined ${network.ssid}. Coming back to your Wi-Fi…")
            local.leaveSetup()
            val ip = findOnHome(outcome.ip, name, local)
            if (ip != null) onDone(ip) else step = Step.Failed(
                "The amp joined ${network.ssid} at ${outcome.ip}, but this phone can't reach it. " +
                    "Is the phone on the same Wi-Fi?",
            )
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .imePadding()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("Amp Wi-Fi", style = MaterialTheme.typography.headlineMedium)
        if (name.isNotEmpty()) Hint(name)
        when (val s = step) {
            Step.Joining -> Busy("Looking for the amp's setup network. Android will ask to connect to it.")
            is Step.Waiting -> Busy(s.text)
            is Step.Picking -> {
                s.note?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                Text("Pick the Wi-Fi the amp should use")
                LazyColumn(Modifier.weight(1f)) {
                    items(s.networks, key = { it.ssid }) { network ->
                        NetworkRow(network) {
                            if (network.secure) step = Step.Password(network) else send(network, "")
                        }
                        HorizontalDivider()
                    }
                }
                TextButton(onClick = {
                    val setup = client ?: return@TextButton
                    scope.launch { step = Step.Picking(runCatching { setup.networks() }.getOrDefault(s.networks)) }
                }) { Text("Search again") }
            }
            is Step.Password -> {
                var psk by remember(s) { mutableStateOf("") }
                var shown by remember(s) { mutableStateOf(false) }
                Text(s.network.ssid, style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = psk,
                    onValueChange = { psk = it },
                    label = { Text("Wi-Fi password") },
                    singleLine = true,
                    visualTransformation = if (shown) VisualTransformation.None else PasswordVisualTransformation(),
                    trailingIcon = {
                        IconButton(onClick = { shown = !shown }) {
                            Icon(
                                if (shown) Icons.Outlined.VisibilityOff else Icons.Outlined.Visibility,
                                contentDescription = if (shown) "Hide the password" else "Show the password",
                            )
                        }
                    },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, autoCorrectEnabled = false),
                    modifier = Modifier.fillMaxWidth(),
                )
                Button(
                    onClick = { send(s.network, psk) },
                    enabled = psk.length in 8..63,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Connect") }
                TextButton(onClick = {
                    val setup = client ?: return@TextButton
                    scope.launch { step = Step.Picking(runCatching { setup.networks() }.getOrDefault(emptyList())) }
                }) { Text("Back") }
            }
            is Step.Failed -> {
                Text(s.why, color = MaterialTheme.colorScheme.error)
                if (local.canJoinSetup) {
                    Button(onClick = { attempt++ }, Modifier.fillMaxWidth()) { Text("Try again") }
                }
                Hint("The amp opens its setup network when it has no working Wi-Fi.")
            }
        }
        TextButton(onClick = onCancel, Modifier.align(Alignment.End)) { Text("Cancel") }
    }
}

@Composable
private fun Busy(text: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        CircularProgressIndicator()
        Text(text)
    }
}

@Composable
private fun NetworkRow(network: WifiNetwork, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 14.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Outlined.Wifi, contentDescription = null)
        Text(network.ssid, Modifier.weight(1f))
        if (network.secure) Icon(Icons.Outlined.Lock, contentDescription = "Needs a password")
    }
}

/**
 * The bridge on the home network, once the phone is back on it: first at the IP it reported, then by discovery
 * (by name), for up to [waitMs].
 */
private suspend fun findOnHome(ip: String, name: String, local: LocalNetwork, waitMs: Long = 30_000): String? {
    val bridge = BridgeClient(ip)
    var waited = 0L
    while (waited < waitMs) {
        if (runCatching { bridge.device() }.isSuccess) return ip
        val found = runCatching { discover(open = local::wifiSocket) }.getOrDefault(emptyList())
        found.firstOrNull { it.name == name || it.ip == ip }?.let { return it.ip }
        delay(2_000)
        waited += 2_000 + 2_100
    }
    return null
}
