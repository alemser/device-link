package com.alemser.amplink.core

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiNetworkSpecifier
import android.os.Build
import android.os.PatternMatcher
import androidx.annotation.RequiresApi
import kotlinx.coroutines.suspendCancellableCoroutine
import okhttp3.OkHttpClient
import java.io.IOException
import java.net.DatagramSocket
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/** Android's side of the Wi-Fi setup: the phone's Wi-Fi, and joining a bridge's setup network. */
class LocalNetwork(context: Context) {
    private val connectivity = context.getSystemService(ConnectivityManager::class.java)
    private var setupCallback: ConnectivityManager.NetworkCallback? = null

    /** Joining from the app needs Android 10; before that, the person joins in the Wi-Fi settings. */
    val canJoinSetup get() = Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q

    /** A socket on the phone's Wi-Fi, so the discovery broadcast doesn't go out on mobile data. */
    fun wifiSocket(): DatagramSocket {
        val socket = DatagramSocket()
        wifi()?.let { runCatching { it.bindSocket(socket) } }
        return socket
    }

    @Suppress("DEPRECATION")      // allNetworks: still the simple way to look at every network
    private fun wifi(): Network? = connectivity.allNetworks.firstOrNull {
        connectivity.getNetworkCapabilities(it)?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true
    }

    /**
     * Asks Android to join a network whose name starts with [SETUP_PREFIX]. Android shows its own dialog with the
     * matching networks; the person picks one. Returns an HTTP client bound to that network and its name.
     * The phone stays on it until [leaveSetup].
     */
    @RequiresApi(Build.VERSION_CODES.Q)
    suspend fun joinSetup(): Pair<OkHttpClient, String> = suspendCancellableCoroutine { waiting ->
        leaveSetup()
        val specifier = WifiNetworkSpecifier.Builder()
            .setSsidPattern(PatternMatcher(SETUP_PREFIX, PatternMatcher.PATTERN_PREFIX))
            .setWpa2Passphrase(SETUP_KEY)
            .build()
        val request = NetworkRequest.Builder()
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .setNetworkSpecifier(specifier)
            .build()
        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                val http = OkHttpClient.Builder().socketFactory(network.socketFactory).build()
                val ssid = setupSsid(network)
                if (waiting.isActive) waiting.resume(http to ssid)
            }

            override fun onUnavailable() {
                if (waiting.isActive) waiting.resumeWithException(IOException("Didn't join the amp's setup network"))
            }
        }
        setupCallback = callback
        waiting.invokeOnCancellation { leaveSetup() }
        connectivity.requestNetwork(request, callback)
    }

    @RequiresApi(Build.VERSION_CODES.Q)
    private fun setupSsid(network: Network): String {
        val info = connectivity.getNetworkCapabilities(network)?.transportInfo
        val ssid = (info as? android.net.wifi.WifiInfo)?.ssid?.trim('"').orEmpty()
        return if (ssid.startsWith(SETUP_PREFIX)) ssid else ""
    }

    /** Gives the setup network back: the phone returns to its own Wi-Fi by itself. */
    fun leaveSetup() {
        setupCallback?.let { runCatching { connectivity.unregisterNetworkCallback(it) } }
        setupCallback = null
    }
}
