package com.rommelguerra.prototipomusichaptic.ui.screens

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.rommelguerra.prototipomusichaptic.R
import com.rommelguerra.prototipomusichaptic.models.NoteModel
import com.rommelguerra.prototipomusichaptic.ui.components.BottomNavBar
import com.rommelguerra.prototipomusichaptic.ui.navigation.Screen
import com.rommelguerra.prototipomusichaptic.ui.theme.*
import com.rommelguerra.prototipomusichaptic.ui.viewmodels.MainMenuViewModel

@Composable
fun MainMenuScreen(
    onNavigate: (String) -> Unit,
    viewModel: MainMenuViewModel = viewModel()
) {
    val context = LocalContext.current
    
    val permissionsLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        if (permissions.values.all { it }) {
            viewModel.startScan()
        }
    }

    val bluetoothEnableLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            viewModel.startScan()
        }
    }

    LaunchedEffect(Unit) {
        val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        val adapter = bluetoothManager.adapter
        
        if (adapter != null && adapter.isEnabled) {
            val permissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.ACCESS_FINE_LOCATION)
            } else {
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
            }
            
            if (permissions.all { ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED }) {
                viewModel.startScan()
            }
        }
    }

    Scaffold(
        bottomBar = {
            BottomNavBar(currentScreen = Screen.MainMenu.route, onNavigate = onNavigate)
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .background(Color.White)
                .verticalScroll(rememberScrollState())
        ) {
            // Header: Profile Icon + Welcome
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 24.dp, vertical = 32.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(60.dp)
                        .border(1.dp, Color(0xFFFF5252), CircleShape)
                        .clip(CircleShape)
                        .clickable { onNavigate(Screen.Profile.route) }
                        .padding(4.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        painter = painterResource(id = R.drawable.usuario),
                        contentDescription = "Perfil",
                        modifier = Modifier.size(40.dp),
                        tint = Color.Unspecified
                    )
                }
                
                Text(
                    text = "Bienvenido ${viewModel.userName}",
                    modifier = Modifier.weight(1f),
                    textAlign = TextAlign.Center,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color.Black
                )
            }

            Text(
                text = "Conoce todas las Notas",
                modifier = Modifier.padding(start = 24.dp, bottom = 16.dp),
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                color = Color.Black
            )
            
            // Notes Row (Dark Cards)
            LazyRow(
                contentPadding = PaddingValues(horizontal = 24.dp),
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                items(viewModel.notes) { nota ->
                    DarkNoteCard(nota = nota) {
                        viewModel.playNote(nota)
                    }
                }
            }

            Spacer(modifier = Modifier.height(32.dp))

            // Binding Section
            Column(modifier = Modifier.padding(horizontal = 24.dp)) {
                Text(
                    text = "Vincular dispositivo",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.Black
                )
                
                Spacer(modifier = Modifier.height(12.dp))

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFF8F9FA)),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = viewModel.statusText,
                                fontSize = 16.sp,
                                color = Color.Black
                            )
                            
                            Button(
                                onClick = {
                                    val bluetoothManager = context.getSystemService(android.content.Context.BLUETOOTH_SERVICE) as android.bluetooth.BluetoothManager
                                    val adapter = bluetoothManager.adapter

                                    if (adapter == null) {
                                        Toast.makeText(context, "Bluetooth no compatible", Toast.LENGTH_SHORT).show()
                                        return@Button
                                    }

                                    if (!adapter.isEnabled) {
                                        val enableBtIntent = android.content.Intent(android.bluetooth.BluetoothAdapter.ACTION_REQUEST_ENABLE)
                                        bluetoothEnableLauncher.launch(enableBtIntent)
                                        return@Button
                                    }

                                    val permissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                                        arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.ACCESS_FINE_LOCATION)
                                    } else {
                                        arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
                                    }
                                    
                                    val missing = permissions.filter { 
                                        ContextCompat.checkSelfPermission(context, it) != PackageManager.PERMISSION_GRANTED 
                                    }
                                    
                                    if (missing.isEmpty()) {
                                        viewModel.startScan()
                                    } else {
                                        permissionsLauncher.launch(missing.toTypedArray())
                                    }
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = VerdePrimario),
                                shape = RoundedCornerShape(4.dp),
                                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)
                            ) {
                                Text("Activar/Buscar", color = Color.White, fontSize = 14.sp)
                            }
                        }
                        
                        if (viewModel.isScanning) {
                            LinearProgressIndicator(
                                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                                color = VerdePrimario
                            )
                        }

                        Spacer(modifier = Modifier.height(24.dp))
                        
                        Text(
                            text = "Dispositivos Cercanos:",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Medium,
                            color = Color.Black
                        )
                        
                        Spacer(modifier = Modifier.height(12.dp))

                        viewModel.scannedDevices.forEach { device ->
                            DeviceItem(device) {
                                viewModel.connectToDevice(device, context)
                            }
                        }
                    }
                }
            }
        }

        // Feedback Overlay
        AnimatedVisibility(
            visible = viewModel.showFeedback,
            enter = fadeIn(),
            exit = fadeOut()
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(viewModel.feedbackColor.copy(alpha = 0.8f)),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = viewModel.feedbackText,
                    color = Color.White,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
fun DarkNoteCard(nota: NoteModel, onClick: () -> Unit) {
    val nombreBase = nota.nombre.split(" ")[0].uppercase()
    val accentColor = when (nombreBase) {
        "DO" -> Color(0xFFFF5722)
        "DO#" -> Color(0xFF00D166)
        "RE" -> Color(0xFFFFC107)
        "RE#" -> Color(0xFF2196F3)
        "MI" -> Color(0xFFE91E63)
        "FA" -> Color(0xFF9C27B0)
        "SOL" -> Color(0xFF607D8B)
        else -> Color(0xFF00D166)
    }

    Card(
        modifier = Modifier
            .width(160.dp)
            .height(220.dp)
            .clickable { onClick() },
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A1A)),
        shape = RoundedCornerShape(24.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(20.dp))
            
            // Accent line
            Box(
                modifier = Modifier
                    .width(60.dp)
                    .height(3.dp)
                    .background(accentColor, RoundedCornerShape(2.dp))
            )
            
            Spacer(modifier = Modifier.height(24.dp))
            
            Text(text = nombreBase, color = Color.White, fontSize = 40.sp, fontWeight = FontWeight.Bold)
            
            val cifrado = when(nombreBase) {
                "DO" -> "(C)"; "RE" -> "(D)"; "MI" -> "(E)"; "FA" -> "(F)"
                "SOL" -> "(G)"; "LA" -> "(A)"; "SI" -> "(B)"; else -> ""
            }
            if (cifrado.isNotEmpty()) {
                Text(text = cifrado, color = accentColor, fontSize = 18.sp, fontWeight = FontWeight.Medium)
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Text(text = "Nota $nombreBase", color = Color.Gray, fontSize = 12.sp)
            
            Spacer(modifier = Modifier.weight(1f))
            
            Icon(
                Icons.Default.PlayArrow,
                contentDescription = null,
                tint = Color(0xFF00D166),
                modifier = Modifier.size(32.dp).padding(bottom = 12.dp)
            )
        }
    }
}

@SuppressLint("MissingPermission")
@Composable
fun DeviceItem(device: BluetoothDevice, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(Icons.Default.Bluetooth, contentDescription = null, tint = Color.Gray, modifier = Modifier.size(20.dp))
        Spacer(modifier = Modifier.width(12.dp))
        Column {
            Text(text = device.name ?: "Desconocido", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color.Black)
            Text(text = device.address, fontSize = 11.sp, color = Color.Gray)
        }
    }
}
