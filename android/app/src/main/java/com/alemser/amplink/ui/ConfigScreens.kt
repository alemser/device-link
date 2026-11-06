package com.alemser.amplink.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import com.alemser.amplink.core.Config
import com.alemser.amplink.core.ConfigStore
import com.alemser.amplink.core.Device
import com.alemser.amplink.core.InfoConfig
import com.alemser.amplink.core.InfoStatus
import com.alemser.amplink.core.Names
import com.alemser.amplink.core.ScreensStatus
import com.alemser.amplink.core.VuStatus
import com.alemser.amplink.core.centred
import com.alemser.amplink.core.isIpv4
import com.alemser.amplink.core.lcdText
import com.alemser.amplink.core.relayInvalid
import kotlinx.coroutines.launch
import java.util.Locale

private val VU_LAYOUTS = listOf(
    "bars" to "Thin bars",
    "deck" to "Cassette deck",
    "scale" to "Printed scale",
    "kx393" to "Yamaha KX-393",
)

private val INFO_SCREENS = listOf(
    "track" to "Artist and title",
    "pos" to "Track and position",
    "side" to "Time left on the side",
    "stylus" to "Stylus hours",
    "quality" to "Bluetooth quality",
)

private val INFO_NOTES = mapOf("stylus" to "When a side starts", "quality" to "When Bluetooth starts on DAB")

private const val SECS_MIN = 3
private const val SECS_MAX = 60
private const val UTC_MIN = -12.0
private const val UTC_MAX = 14.0
private const val UTC_STEP = 0.25
private const val DEFAULT_COLUMNS = 16

/** The shell of both configuration screens: one `/names` when the screen opens, then only saves. */
@Composable
private fun ConfigPage(
    store: ConfigStore,
    modifier: Modifier,
    content: @Composable (Config, Names) -> Unit,
) {
    val scope = rememberCoroutineScope()
    LaunchedEffect(store) { store.load() }
    val config = store.config
    val names = store.names
    Column(
        modifier
            .fillMaxSize()
            .imePadding()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        when {
            config != null && names != null -> {
                SaveLine(store.save, store::retry)
                content(config, names)
            }
            store.loadError != null -> {
                Text("Couldn't load: ${store.loadError}", color = MaterialTheme.colorScheme.error)
                TextButton(onClick = { scope.launch { store.load() } }) { Text("Try again") }
            }
            else -> CircularProgressIndicator(Modifier.align(Alignment.CenterHorizontally))
        }
    }
}

@Composable
fun DisplayScreen(store: ConfigStore, device: Device, modifier: Modifier = Modifier) {
    ConfigPage(store, modifier) { config, names ->
        if (device.has("vu")) VuSection(store, config, names.vu)
        if (device.has("info_screens")) InfoSection(store, config.info, config, names)
    }
}

@Composable
private fun VuSection(store: ConfigStore, config: Config, status: VuStatus?) {
    val vu = config.vu
    fun set(change: (com.alemser.amplink.core.VuConfig) -> com.alemser.amplink.core.VuConfig) =
        store.edit { it.copy(vu = change(it.vu)) }
    Section("VU meter") {
        SwitchRow("Show the VU meter", vu.on, vuText(status, vu.relay)) { on -> set { it.copy(on = on) } }
        if (vu.on) {
            Column {
                VU_LAYOUTS.forEach { (key, name) ->
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .selectable(vu.layout == key) { set { it.copy(layout = key) } },
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RadioButton(selected = vu.layout == key, onClick = null, modifier = Modifier.padding(10.dp))
                        Text(name)
                    }
                }
            }
        }
        IpField("VU source (IP)", vu.relay, relayInvalid(vu)) { ip -> set { it.copy(relay = ip) } }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun InfoSection(store: ConfigStore, info: InfoConfig, config: Config, names: Names) {
    fun set(change: (InfoConfig) -> InfoConfig) = store.edit { it.copy(info = change(it.info)) }
    Section("Info screens") {
        SwitchRow("Show what is playing", info.on, infoText(names.info, names.screens)) { on -> set { it.copy(on = on) } }
        if (info.on) {
            Hint("While playing")
            SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                listOf("temp" to "On track change", "fixed" to "All the time").forEachIndexed { i, (key, name) ->
                    SegmentedButton(
                        selected = info.mode == key,
                        onClick = { set { it.copy(mode = key) } },
                        shape = SegmentedButtonDefaults.itemShape(i, 2),
                    ) { Text(name, maxLines = 1) }
                }
            }
            if (info.mode == "fixed") {
                Column {
                    INFO_SCREENS.forEach { (key, name) ->
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .selectable(info.fixed == key) { set { it.copy(fixed = key) } },
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            RadioButton(selected = info.fixed == key, onClick = null, modifier = Modifier.padding(10.dp))
                            Text(name)
                        }
                    }
                }
                Hint("The VU meter is not shown in this mode")
            } else {
                Stepper(
                    "Seconds per screen",
                    "${info.secs} s",
                    info.secs > SECS_MIN,
                    info.secs < SECS_MAX,
                    { set { it.copy(secs = it.secs - 1) } },
                    { set { it.copy(secs = it.secs + 1) } },
                )
                Column {
                    INFO_SCREENS.forEach { (key, name) ->
                        CheckRow(name, key in info.show, INFO_NOTES[key]) { on ->
                            set { it.copy(show = if (on) it.show + key else it.show - key) }
                        }
                    }
                }
            }
        }
    }
    if (info.on) {
        Section("Turntable inputs") {
            Hint("The stylus screen and the end-of-side warning only appear on these")
            Column {
                names.inputs.forEach { input ->
                    CheckRow(config.inputs[input]?.ifEmpty { null } ?: input, input in info.turntable) { on ->
                        set { it.copy(turntable = if (on) it.turntable + input else it.turntable - input) }
                    }
                }
            }
            SwitchRow("End of side", info.alert, "Last minute and \"Flip the record\"") { on ->
                set { it.copy(alert = on) }
            }
        }
        Section("Clock and text") {
            SwitchRow("Clock in standby", info.clock) { on -> set { it.copy(clock = on) } }
            SwitchRow("Scroll long names", info.scroll) { on -> set { it.copy(scroll = on) } }
            Stepper(
                "UTC offset",
                String.format(Locale.US, "%+.2f h", info.utcOffset),
                info.utcOffset > UTC_MIN,
                info.utcOffset < UTC_MAX,
                { set { it.copy(utcOffset = it.utcOffset - UTC_STEP) } },
                { set { it.copy(utcOffset = it.utcOffset + UTC_STEP) } },
            )
            SwitchRow("Summer time", info.euDst, "European rule (+1 h)") { on -> set { it.copy(euDst = on) } }
        }
        Section("Source") {
            IpField(
                "Info source (IP)",
                info.source,
                info.source.isNotEmpty() && !isIpv4(info.source),
                "Same as the VU source",
            ) { ip -> set { it.copy(source = ip) } }
        }
    }
}

private fun vuText(status: VuStatus?, relay: String): String = when {
    status?.error != null -> "Turned off after an error: ${status.error}"
    status == null || !status.on -> "Off"
    status.showing -> "On the display now, scale ${status.floor} to ${status.top} dB"
    status.lastFrameMs == null || status.lastFrameMs > 1000 -> "No data from $relay. Is the VU relay running there?"
    status.music -> "Amp screen for a moment"
    else -> "Waiting for music"
}

private fun infoText(info: InfoStatus?, screens: ScreensStatus?): String {
    if (screens?.error != null) return "Turned off after an error: ${screens.error}"
    if (screens == null || !screens.on || info == null) return "Off"
    if (info.lastPacketMs == null || info.lastPacketMs > 15_000) return "No data from the info source. Is the VU relay running there?"
    val now = when {
        info.playing && info.title != null -> "Playing: " + listOfNotNull(info.artist, info.title).joinToString(" – ")
        info.stream != null -> "Streaming: ${info.stream}"
        info.sideEnd -> "Side ended"
        else -> "Nothing playing"
    }
    return now + (screens.showing?.let { " · on the display: $it" } ?: "")
}

@Composable
fun NamesScreen(store: ConfigStore, device: Device, modifier: Modifier = Modifier) {
    val columns = device.display?.columns ?: DEFAULT_COLUMNS
    ConfigPage(store, modifier) { config, names ->
        Section("Inputs") {
            names.inputs.forEach { input ->
                LcdField(input, config.inputs[input].orEmpty(), input, columns) { text ->
                    store.edit { it.copy(inputs = it.inputs + (input to text)) }
                }
            }
        }
        StartupSection("Startup screen", config.boot, names.defaults.boot, columns) { lines ->
            store.edit { it.copy(boot = lines) }
        }
        StartupSection("About screen", config.about, names.defaults.about, columns) { lines ->
            store.edit { it.copy(about = lines) }
        }
    }
}

@Composable
private fun StartupSection(
    title: String,
    lines: List<String>,
    defaults: List<String>,
    columns: Int,
    onChange: (List<String>) -> Unit,
) {
    Section(title) {
        Lcd(lines.mapIndexed { i, line -> centred(line.ifEmpty { defaults[i] }, columns) }, columns)
        lines.forEachIndexed { i, line ->
            LcdField("Line ${i + 1}", line, defaults[i], columns) { text ->
                onChange(lines.toMutableList().also { it[i] = text })
            }
        }
    }
}

/** Text for the LCD: only what it can show fits in, so the bridge never refuses it. */
@Composable
private fun LcdField(label: String, value: String, placeholder: String, columns: Int, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = { onChange(lcdText(it, columns)) },
        label = { Text(label) },
        placeholder = { Text(placeholder, fontFamily = FontFamily.Monospace) },
        supportingText = { Text("${value.length}/$columns") },
        textStyle = MaterialTheme.typography.bodyLarge.copy(fontFamily = FontFamily.Monospace),
        singleLine = true,
        modifier = Modifier.fillMaxWidth(),
    )
}
