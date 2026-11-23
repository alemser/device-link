package com.alemser.amplink.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.text.TextStyle
import com.alemser.amplink.core.StateField
import com.alemser.amplink.core.argb
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import java.io.IOException

/** One command at a time: a bridge may take seconds (an amp's menus), and a second press meanwhile is dropped. */
class Commands(private val scope: CoroutineScope) {
    var working by mutableStateOf(false)
        private set
    var error by mutableStateOf<String?>(null)
        private set

    fun run(command: suspend () -> Unit) {
        if (working) return
        working = true
        error = null
        scope.launch {
            try {
                command()
            } catch (e: IOException) {
                error = e.message ?: "The device didn't answer"
            } finally {
                working = false
            }
        }
    }
}

/** The amp's blue display, the one strong colour in the app. */
val LcdBlue = Color(0xFF2C4FD6)
val LcdText = Color(0xFFEEEEFF)
val Warning = Color(0xFFE8A04A)

private val Dark = darkColorScheme(
    primary = Color(0xFF9DB0FF),
    onPrimary = Color(0xFF10205F),
    primaryContainer = LcdBlue,
    onPrimaryContainer = LcdText,
    background = Color(0xFF141414),
    surface = Color(0xFF141414),
    surfaceContainer = Color(0xFF1F1F1F),
    surfaceContainerLow = Color(0xFF1F1F1F),
)

private val Light = lightColorScheme(
    primary = LcdBlue,
    onPrimary = Color.White,
    background = Color(0xFFF4F4F2),
    surface = Color(0xFFF4F4F2),
    surfaceContainer = Color.White,
    surfaceContainerLow = Color.White,
)

@Composable
fun AmpLinkTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (isSystemInDarkTheme()) Dark else Light, content = content)
}

/** How a display looks: its glass, its text, and whether the text glows (a VFD) or is printed (an LCD). */
data class LcdLook(val glass: Color = LcdBlue, val ink: Color = LcdText, val glow: Boolean = false)

/** The look a `lines` field asks for (docs/contract-v2.md, State fields); the app's blue for what it doesn't say. */
fun lookOf(field: StateField) = LcdLook(
    glass = argb(field.glass)?.let { Color(it) } ?: LcdBlue,
    ink = argb(field.ink)?.let { Color(it) } ?: LcdText,
    glow = field.glow,
)

/** The device's display, with the text sized so that every column fits the width (up to [MAX_SP]). */
@Composable
fun Lcd(lines: List<String>, columns: Int, modifier: Modifier = Modifier, dim: Boolean = false, look: LcdLook = LcdLook()) {
    // A VFD's glow halos each letter; on a dim (not live) display the whole glass fades, as the real one does.
    val glow = if (look.glow) Shadow(look.ink.copy(alpha = 0.75f), Offset.Zero, blurRadius = 14f) else null
    BoxWithConstraints(
        modifier
            .fillMaxWidth()
            .alpha(if (dim) 0.5f else 1f)
            .clip(RoundedCornerShape(10.dp))
            .background(look.glass)
            .padding(horizontal = 14.dp, vertical = 12.dp),
    ) {
        val fit = with(LocalDensity.current) { (maxWidth / columns / MONOSPACE_ADVANCE).toSp() }
        val size = if (fit.value > MAX_SP) MAX_SP.sp else fit
        Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
            lines.forEach {
                Text(
                    it.padEnd(columns).take(columns),
                    color = look.ink,
                    fontFamily = FontFamily.Monospace,
                    fontSize = size,
                    style = TextStyle(shadow = glow),
                    maxLines = 1,
                    softWrap = false,
                )
            }
        }
    }
}

/** Android's monospace face is 0.6 em wide; the rest is a margin so the last column never wraps. */
private const val MONOSPACE_ADVANCE = 0.62f

/** Never larger than this, even for a narrow display on a wide phone. */
private const val MAX_SP = 26f

@Composable
fun Section(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(
            title,
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 4.dp),
        )
        Surface(
            shape = RoundedCornerShape(14.dp),
            color = MaterialTheme.colorScheme.surfaceContainer,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp), content = content)
        }
    }
}

@Composable
fun Hint(text: String, color: Color = MaterialTheme.colorScheme.onSurfaceVariant) {
    Text(text, style = MaterialTheme.typography.bodySmall, color = color)
}

@Composable
fun SwitchRow(label: String, checked: Boolean?, hint: String? = null, onChange: (Boolean) -> Unit) {
    if (checked == null) {
        // Unknown is not off (docs/contract-v2.md, "For the app" 5): no switch position to guess, both choices offered.
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(label)
                Hint(hint ?: "Unknown")
            }
            TextButton(onClick = { onChange(false) }) { Text("Off") }
            TextButton(onClick = { onChange(true) }) { Text("On") }
        }
        return
    }
    Row(
        Modifier
            .fillMaxWidth()
            .clickable { onChange(!checked) },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(label)
            hint?.let { Hint(it) }
        }
        Switch(checked = checked, onCheckedChange = onChange)
    }
}

/** A number in a fixed range, changed with − and + so it can never be invalid. */
@Composable
fun Stepper(label: String, value: String, canDown: Boolean, canUp: Boolean, onDown: () -> Unit, onUp: () -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, Modifier.weight(1f))
        TextButton(onClick = onDown, enabled = canDown) { Text("−", style = MaterialTheme.typography.titleLarge) }
        Text(value, Modifier.padding(horizontal = 4.dp), textAlign = TextAlign.Center)
        TextButton(onClick = onUp, enabled = canUp) { Text("+", style = MaterialTheme.typography.titleLarge) }
    }
}
