require('dotenv').config();
const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

// Parsea JSON hasta 20 MB (necesario para los frames en base64)
app.use(express.json({ limit: '20mb' }));

// Sirve la carpeta 'public' (index.html, client.js, etc.)
app.use(express.static('public'));

// Endpoint para recibir y procesar frames
app.post('/analyze', (req, res) => {
  const { image } = req.body;
  if (!image) {
    return res.status(400).json({ error: 'Falta campo image' });
  }
  
  console.log('Frame recibido para análisis (bytes):', image.length);
  // Aquí es donde luego llamaremos a Gemini Vision
  res.json({ status: 'received' });
});

// Arranca el servidor
app.listen(port, () => {
  console.log(`DJ interactivo corriendo en http://localhost:${port}`);
});
