<script>
  import { onMount, onDestroy } from 'svelte';
  import io from 'socket.io-client';
  
  let socket;
  let cameraActive = false;
  let currentFrame = '';
  let analysis = null;
  let djPhrase = '';
  let selectedVoiceModel = 'bad_bunny';
  let frameInterval;
  let currentAudio = null; // Para gestionar la reproducción
  
  const voiceModels = [
    { id: 'bad_bunny', name: '🐰 Bad Bunny', emoji: '🐰' },
    { id: 'bob_sponge', name: '🧽 Bob Esponja', emoji: '🧽' }
  ];
  
  onMount(() => {
    // Conectar al servidor WebSocket
    socket = io('http://localhost:5000');
    
    socket.on('connect', () => {
      console.log('Conectado al servidor');
    });
    
    socket.on('analysis_update', (data) => {
      analysis = data.analysis;
      djPhrase = data.dj_phrase;
      
      // Si recibimos audio, lo reproducimos
      if (data.audio_base64) {
        playAudio(data.audio_base64);
      }
    });
    
    socket.on('frame_update', (data) => {
      currentFrame = `data:image/jpeg;base64,${data.frame}`;
    });
    
    socket.on('camera_started', () => {
      cameraActive = true;
      startFrameCapture();
    });
    
    socket.on('camera_stopped', () => {
      cameraActive = false;
      stopFrameCapture();
    });
    
    socket.on('error', (data) => {
      alert(`Error: ${data.message}`);
    });
  });
  
  onDestroy(() => {
    stopFrameCapture();
    if (socket) {
      socket.disconnect();
    }
  });
  
  function startCamera() {
    socket.emit('start_camera');
  }
  
  function stopCamera() {
    socket.emit('stop_camera');
  }
  
  function startFrameCapture() {
    if (frameInterval) clearInterval(frameInterval);
    frameInterval = setInterval(() => {
      if (cameraActive && socket) {
        socket.emit('get_frame');
      }
    }, 100); // Solicitar frame cada 100ms
  }
  
  function stopFrameCapture() {
    if (frameInterval) {
      clearInterval(frameInterval);
      frameInterval = null;
    }
  }
  
  function handleVoiceModelChange() {
    // Enviar la selección de voz al backend
    if (socket) {
      socket.emit('change_voice_model', { voice_model: selectedVoiceModel });
      console.log('Modelo de voz seleccionado:', selectedVoiceModel);
    }
  }
  
  function getEnergyColor(nivel) {
    if (nivel <= 3) return '#ff4444';
    if (nivel <= 6) return '#ffaa00';
    return '#44ff44';
  }

  // --- FUNCIÓN PARA REPRODUCIR AUDIO DESDE BASE64 ---
  function playAudio(base64String) {
    if (currentAudio && !currentAudio.paused) {
      currentAudio.pause(); // Detener el audio anterior si aún se está reproduciendo
    }
    const audioSource = `data:audio/mpeg;base64,${base64String}`;
    currentAudio = new Audio(audioSource);
    currentAudio.play().catch(e => {
      // Los navegadores modernos bloquean el autoplay hasta la primera interacción del usuario.
      // El clic en "Iniciar Cámara" ya cuenta como una interacción, por lo que esto debería funcionar.
      console.error("Error al reproducir audio:", e);
    });
  }
</script>

<main>
  <div class="container">
    <header>
      <h1>🎧 DJ Huevito AI</h1>
      <p>Sistema de análisis de ambiente en tiempo real</p>
    </header>
    
    <div class="controls">
      <div class="camera-controls">
        <button 
          class="btn {cameraActive ? 'btn-danger' : 'btn-primary'}"
          on:click={cameraActive ? stopCamera : startCamera}
        >
          {cameraActive ? '⏹️ Detener Cámara' : '▶️ Iniciar Cámara'}
        </button>
        
        <div class="status">
          Estado: <span class="status-indicator {cameraActive ? 'active' : 'inactive'}">
            {cameraActive ? '🟢 Activa' : '🔴 Inactiva'}
          </span>
        </div>
      </div>
      
      <div class="voice-controls">
        <label for="voice-model">🎤 Seleccionar DJ:</label>
        <div class="voice-selector">
          {#each voiceModels as model}
            <button 
              class="voice-option {selectedVoiceModel === model.id ? 'selected' : ''}"
              on:click={() => {
                selectedVoiceModel = model.id;
                handleVoiceModelChange();
              }}
            >
              <span class="voice-emoji">{model.emoji}</span>
              <span class="voice-name">{model.name.replace(model.emoji, '').trim()}</span>
            </button>
          {/each}
        </div>
      </div>
    </div>

    <div class="content-grid">
      <!-- Video Feed -->
      <div class="video-section">
        <h2>📹 Feed de Video</h2>
        <div class="video-container">
          {#if currentFrame}
            <img src={currentFrame} alt="Video feed" class="video-feed" />
          {:else}
            <div class="no-video">
              <p>No hay video disponible</p>
              <p>Inicia la cámara para ver el feed</p>
            </div>
          {/if}
        </div>
      </div>

      <!-- Analysis Section -->
      <div class="analysis-section">
        <h2>📊 Análisis del Ambiente</h2>
        {#if analysis}
          <div class="analysis-card">
            <div class="analysis-item">
              <strong>Descripción:</strong>
              <p>{analysis.descripcion_general || 'N/A'}</p>
            </div>
            
            <div class="analysis-item">
              <strong>Nivel de Energía:</strong>
              <div class="energy-display">
                <span 
                  class="energy-level" 
                  style="color: {getEnergyColor(analysis.nivel_energia)}"
                >
                  {analysis.nivel_energia || 'N/A'} / 10
                </span>
                <div class="energy-bar">
                  <div 
                    class="energy-fill" 
                    style="width: {(analysis.nivel_energia || 0) * 10}%; background-color: {getEnergyColor(analysis.nivel_energia)}"
                  ></div>
                </div>
              </div>
            </div>
            
            <div class="analysis-item">
              <strong>¿Gente Bailando?:</strong>
              <span class="indicator {analysis.personas_bailando ? 'positive' : 'negative'}">
                {analysis.personas_bailando ? '✅ Sí' : '❌ No'}
              </span>
            </div>
            
            <div class="analysis-item">
              <strong>¿Gente Aburrida?:</strong>
              <span class="indicator {analysis.personas_aburridas ? 'negative' : 'positive'}">
                {analysis.personas_aburridas ? '😴 Sí' : '😊 No'}
              </span>
            </div>
            
            <div class="analysis-item">
              <strong>Número de Personas:</strong>
              <span>{analysis.numero_personas || 0}</span>
            </div>
          </div>
        {:else}
          <div class="no-analysis">
            <p>No hay análisis disponible</p>
            <p>Inicia la cámara para comenzar el análisis</p>
          </div>
        {/if}
      </div>

      <!-- DJ Phrase Section -->
      <div class="dj-section">
        <h2>🎤 {voiceModels.find(v => v.id === selectedVoiceModel)?.name || 'DJ Huevito AI'}</h2>
        {#if djPhrase}
          <div class="dj-phrase-card">
            <div class="dj-avatar">
              {voiceModels.find(v => v.id === selectedVoiceModel)?.emoji || '🥚'}🎧
            </div>
            <div class="dj-bubble">
              <p>"{djPhrase}"</p>
            </div>
          </div>
        {:else}
          <div class="no-dj">
            <div class="dj-avatar">
              {voiceModels.find(v => v.id === selectedVoiceModel)?.emoji || '🥚'}😴
            </div>
            <p>{voiceModels.find(v => v.id === selectedVoiceModel)?.name.replace(voiceModels.find(v => v.id === selectedVoiceModel)?.emoji || '', '').trim() || 'DJ Huevito'} está esperando...</p>
          </div>
        {/if}
      </div>
    </div>
  </div>
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    color: #333;
    line-height: 1.6;
  }

  :global(*) {
    box-sizing: border-box;
  }

  .container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
    min-height: 100vh;
  }

  header {
    text-align: center;
    margin-bottom: 40px;
    color: white;
    animation: fadeInDown 0.8s ease-out;
  }

  header h1 {
    font-size: 3.5rem;
    font-weight: 800;
    margin: 0 0 10px 0;
    text-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    background: linear-gradient(45deg, #fff, #f0f0f0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  header p {
    font-size: 1.2rem;
    margin: 0;
    opacity: 0.9;
    font-weight: 300;
  }

  .controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 25px;
    margin-bottom: 30px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    animation: fadeInUp 0.8s ease-out 0.2s both;
  }

  .camera-controls {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .btn {
    padding: 12px 24px;
    border: none;
    border-radius: 12px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    position: relative;
    overflow: hidden;
  }

  .btn::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s;
  }

  .btn:hover::before {
    left: 100%;
  }

  .btn-primary {
    background: linear-gradient(45deg, #4CAF50, #45a049);
    color: white;
    box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4);
  }

  .btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(76, 175, 80, 0.6);
  }

  .btn-danger {
    background: linear-gradient(45deg, #f44336, #d32f2f);
    color: white;
    box-shadow: 0 4px 15px rgba(244, 67, 54, 0.4);
  }

  .btn-danger:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(244, 67, 54, 0.6);
  }

  .status {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 500;
  }

  .status-indicator {
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: 600;
  }

  .status-indicator.active {
    background: rgba(76, 175, 80, 0.2);
    color: #4CAF50;
    border: 1px solid rgba(76, 175, 80, 0.3);
  }

  .status-indicator.inactive {
    background: rgba(244, 67, 54, 0.2);
    color: #f44336;
    border: 1px solid rgba(244, 67, 54, 0.3);
  }

  .voice-controls {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .voice-controls label {
    color: white;
    font-weight: 500;
  }

  .voice-selector {
    display: flex;
    gap: 10px;
  }

  .voice-option {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.1);
    color: white;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
    min-width: 140px;
    justify-content: center;
  }

  .voice-option:hover {
    transform: translateY(-2px);
    border-color: rgba(255, 255, 255, 0.6);
    box-shadow: 0 4px 15px rgba(255, 255, 255, 0.2);
  }

  .voice-option.selected {
    border-color: #4CAF50;
    background: rgba(76, 175, 80, 0.2);
    box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
  }

  .voice-emoji {
    font-size: 1.2rem;
  }

  .voice-name {
    font-weight: 500;
  }

  .content-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
    animation: fadeInUp 0.8s ease-out 0.4s both;
  }

  .video-section, .analysis-section, .dj-section {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 25px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
  }

  .video-section:hover, .analysis-section:hover, .dj-section:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  }

  .dj-section {
    grid-column: 1 / -1;
  }

  h2 {
    color: white;
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0 0 20px 0;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .video-container {
    position: relative;
    border-radius: 15px;
    overflow: hidden;
    background: rgba(0, 0, 0, 0.3);
    min-height: 300px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .video-feed {
    width: 100%;
    height: auto;
    border-radius: 15px;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
  }

  .no-video {
    text-align: center;
    color: rgba(255, 255, 255, 0.7);
    padding: 40px;
  }

  .no-video p {
    margin: 10px 0;
    font-size: 1.1rem;
  }

  .analysis-card {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .analysis-item {
    background: rgba(255, 255, 255, 0.05);
    padding: 15px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .analysis-item strong {
    color: white;
    display: block;
    margin-bottom: 8px;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .analysis-item p, .analysis-item span {
    color: rgba(255, 255, 255, 0.9);
    margin: 0;
    font-size: 1rem;
  }

  .energy-display {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .energy-level {
    font-size: 1.2rem;
    font-weight: 700;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  }

  .energy-bar {
    width: 100%;
    height: 8px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 4px;
    overflow: hidden;
  }

  .energy-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
    box-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
  }

  .indicator {
    font-weight: 600;
    font-size: 1.1rem;
  }

  .indicator.positive {
    color: #4CAF50;
  }

  .indicator.negative {
    color: #f44336;
  }

  .no-analysis {
    text-align: center;
    color: rgba(255, 255, 255, 0.7);
    padding: 40px;
  }

  .no-analysis p {
    margin: 10px 0;
    font-size: 1.1rem;
  }

  .dj-phrase-card {
    display: flex;
    align-items: flex-start;
    gap: 20px;
    background: rgba(255, 255, 255, 0.05);
    padding: 25px;
    border-radius: 15px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .dj-avatar {
    font-size: 3rem;
    animation: bounce 2s infinite;
  }

  .dj-bubble {
    flex: 1;
    background: linear-gradient(45deg, #ff6b6b, #ee5a24);
    padding: 20px;
    border-radius: 20px;
    position: relative;
    box-shadow: 0 8px 25px rgba(255, 107, 107, 0.3);
  }

  .dj-bubble::before {
    content: '';
    position: absolute;
    left: -10px;
    top: 20px;
    width: 0;
    height: 0;
    border-top: 10px solid transparent;
    border-bottom: 10px solid transparent;
    border-right: 10px solid #ff6b6b;
  }

  .dj-bubble p {
    color: white;
    font-size: 1.2rem;
    font-weight: 500;
    margin: 0;
    line-height: 1.5;
  }

  .no-dj {
    text-align: center;
    color: rgba(255, 255, 255, 0.7);
    padding: 40px;
  }

  .no-dj p {
    margin: 20px 0 0 0;
    font-size: 1.1rem;
  }

  /* Animations */
  @keyframes fadeInDown {
    from {
      opacity: 0;
      transform: translateY(-30px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(30px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes bounce {
    0%, 20%, 50%, 80%, 100% {
      transform: translateY(0);
    }
    40% {
      transform: translateY(-10px);
    }
    60% {
      transform: translateY(-5px);
    }
  }

  /* Responsive Design */
  @media (max-width: 1024px) {
    .content-grid {
      grid-template-columns: 1fr;
      gap: 20px;
    }
    
    .controls {
      flex-direction: column;
      gap: 20px;
      text-align: center;
    }
    
    .camera-controls {
      flex-direction: column;
      gap: 15px;
    }
    
    .voice-controls {
      flex-direction: column;
      gap: 15px;
    }
    
    .voice-selector {
      flex-direction: column;
      gap: 8px;
    }
    
    .voice-option {
      min-width: auto;
      width: 100%;
    }
  }

  @media (max-width: 768px) {
    .container {
      padding: 15px;
    }
    
    header h1 {
      font-size: 2.5rem;
    }
    
    header p {
      font-size: 1rem;
    }
    
    .controls {
      padding: 20px;
    }
    
    .video-section, .analysis-section, .dj-section {
      padding: 20px;
    }
    
    .dj-phrase-card {
      flex-direction: column;
      text-align: center;
      gap: 15px;
    }
    
    .dj-bubble::before {
      display: none;
    }
  }

  @media (max-width: 480px) {
    header h1 {
      font-size: 2rem;
    }
    
    .btn {
      padding: 10px 20px;
      font-size: 0.9rem;
    }
    
    .dj-avatar {
      font-size: 2.5rem;
    }
    
    .dj-bubble p {
      font-size: 1rem;
    }
  }
</style>