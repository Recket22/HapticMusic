package com.rommelguerra.prototipomusichaptic.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.rommelguerra.prototipomusichaptic.ui.navigation.Screen
import com.rommelguerra.prototipomusichaptic.ui.theme.VerdePrimario
import com.rommelguerra.prototipomusichaptic.ui.viewmodels.LearnViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LearnScreen(
    onNavigate: (String) -> Unit,
    viewModel: LearnViewModel = viewModel()
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { 
                    Text(
                        "Desafío musical", 
                        modifier = Modifier.fillMaxWidth(),
                        textAlign = TextAlign.Center,
                        fontWeight = FontWeight.Bold,
                        fontSize = 24.sp
                    ) 
                },
                navigationIcon = {
                    IconButton(onClick = { onNavigate(Screen.MainMenu.route) }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Volver", modifier = Modifier.size(32.dp))
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .background(Color.White)
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "¡Bienvenido al desafío musical!",
                fontSize = 18.sp,
                fontWeight = FontWeight.Medium,
                color = Color.Black
            )

            Spacer(modifier = Modifier.height(32.dp))

            // Black Square with Play Button
            Box(
                modifier = Modifier
                    .size(220.dp)
                    .background(Color.Black),
                contentAlignment = Alignment.Center
            ) {
                Box(
                    modifier = Modifier
                        .size(120.dp)
                        .border(4.dp, Color(0xFF00D166), CircleShape)
                        .clickable { viewModel.playChallenge() },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        Icons.Default.PlayArrow,
                        contentDescription = "Play",
                        tint = Color(0xFF00D166),
                        modifier = Modifier.size(80.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(32.dp))

            Text(
                text = "¿Que Nota musical reconociste?",
                fontSize = 18.sp,
                color = Color.Black
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Randomized Options Grid
            Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                val chunks = viewModel.challengeOptions.chunked(2)
                chunks.forEach { rowOptions ->
                    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        rowOptions.forEach { note ->
                            val nombreBase = note.nombre.split(" ")[0].uppercase()
                            val cifrado = when(nombreBase) {
                                "DO" -> "(C)"; "RE" -> "(D)"; "MI" -> "(E)"; "FA" -> "(F)"
                                "SOL" -> "(G)"; "LA" -> "(A)"; "SI" -> "(B)"; else -> ""
                            }
                            val displayName = if (cifrado.isNotEmpty()) "$nombreBase $cifrado" else nombreBase
                            
                            val accentColor = when (nombreBase) {
                                "DO" -> Color(0xFFFF5722)
                                "RE" -> Color(0xFFFFC107)
                                "MI" -> Color(0xFFFF5252) // Rojo como en la imagen
                                "FA" -> Color(0xFF2196F3)
                                "SOL" -> Color(0xFF9C27B0)
                                "SI" -> Color(0xFF00D166) // Verde como en la imagen
                                else -> Color(0xFFFFC107) // Amarillo para DO# u otros
                            }

                            NoteChallengeButton(
                                name = displayName, 
                                color = accentColor, 
                                isSelected = viewModel.selectedNoteName == note.nombre,
                                onClick = { viewModel.selectNote(note.nombre) }
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(32.dp))

            if (!viewModel.showResult) {
                Button(
                    onClick = { viewModel.checkAnswer() },
                    modifier = Modifier
                        .width(220.dp)
                        .height(56.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = VerdePrimario),
                    shape = RoundedCornerShape(8.dp),
                    enabled = viewModel.selectedNoteName != null
                ) {
                    Text("Confirmar", color = Color.White, fontSize = 18.sp)
                }
            } else {
                Button(
                    onClick = { viewModel.generateNewChallenge() },
                    modifier = Modifier
                        .width(220.dp)
                        .height(56.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF00D166)),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("Siguiente Desafío", color = Color.White, fontSize = 18.sp)
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = viewModel.feedbackMessage,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
                color = when(viewModel.isSuccess) {
                    true -> Color(0xFF2A703D)
                    false -> Color(0xFFB32626)
                    else -> Color.Black
                }
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Streak indicator
            Box(
                modifier = Modifier
                    .size(100.dp)
                    .background(Color.Black, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Text(text = viewModel.streak.toString(), color = Color(0xFF00D166), fontSize = 32.sp, fontWeight = FontWeight.Bold)
            }
            
            Text(text = "Racha obtenida", modifier = Modifier.padding(top = 8.dp), fontSize = 14.sp, color = Color.Black)

            Spacer(modifier = Modifier.weight(1f))

            Text(
                text = "Juega, Aprende y Diviertete",
                fontSize = 16.sp,
                color = Color.Black,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

@Composable
fun NoteChallengeButton(name: String, color: Color, isSelected: Boolean, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        modifier = Modifier
            .width(160.dp)
            .height(70.dp),
        shape = RoundedCornerShape(4.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = Color(0xFF1A1A1A)
        ),
        border = if (isSelected) androidx.compose.foundation.BorderStroke(3.dp, color) else null
    ) {
        Text(text = name, color = color, fontSize = 18.sp, fontWeight = FontWeight.Bold)
    }
}
