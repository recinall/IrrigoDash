import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

# Definizione dei sensori da visualizzare
SENSORS = {
    'pressure': {'name': 'Pressione', 'unit': 'Bar'},
    'temperature': {'name': 'Temperatura', 'unit': '°C'},
    'humidity': {'name': 'Umidità', 'unit': '%'},
    'env_pressure': {'name': 'Pressione Ambientale', 'unit': 'hPa'}
}

# Percorso del file CSV
CSV_PATH = os.path.expanduser('~/telemetria.csv')

# Massimo numero di punti da visualizzare per sensore
MAX_POINTS = 300

# Funzione per caricare e processare i dati
def process_data(start_date=None, end_date=None):
    try:
        # Carica il CSV
        df = pd.read_csv(CSV_PATH)
        
        # Converti timestamp in datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Converti colonne dei sensori a float
        for sensor in SENSORS.keys():
            if sensor in df.columns:
                df[sensor] = pd.to_numeric(df[sensor], errors='coerce')
        
        # Ordina per timestamp
        df = df.sort_values('timestamp')
        
        # Filtra per date se specificato
        if start_date and end_date:
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date) + timedelta(days=1) - timedelta(seconds=1)
            df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        
        # Calcola le statistiche per ogni sensore
        stats = {}
        chart_data = {}
        
        for sensor in SENSORS.keys():
            if sensor in df.columns:
                sensor_df = df.dropna(subset=[sensor]).copy()
                
                if not sensor_df.empty:
                    # Campionamento e interpolazione
                    sensor_df = sensor_df.set_index('timestamp').sort_index()
                    
                    # Ricampiona a 1 minuto e interpola linearmente
                    sensor_df = sensor_df.resample('min').mean(numeric_only=True)
                    sensor_df[sensor] = pd.to_numeric(sensor_df[sensor], errors='coerce').interpolate(method='linear')
                    
                    # Ricostruisce il dataframe
                    sensor_df = sensor_df.reset_index()
                    sensor_df = sensor_df.dropna(subset=[sensor])
                    
                    # Controlla se il dataframe è vuoto dopo l'interpolazione
                    if sensor_df.empty:
                        stats[sensor] = {'min': 0, 'max': 0, 'mean': 0}
                        continue
                    
                    # Campiona se necessario
                    if len(sensor_df) > MAX_POINTS:
                        indices = np.linspace(0, len(sensor_df) - 1, MAX_POINTS).astype(int)
                        sensor_df = sensor_df.iloc[indices]
                    
                    # Prepara dati per il grafico
                    chart_data[sensor] = {
                        'timestamps': sensor_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                        'values': sensor_df[sensor].tolist()
                    }
                    
                    # Calcola statistiche
                    stats[sensor] = {
                        'min': float(sensor_df[sensor].min()),
                        'max': float(sensor_df[sensor].max()),
                        'mean': float(sensor_df[sensor].mean()),
                        'current': float(sensor_df[sensor].iloc[-1])
                    }
                else:
                    stats[sensor] = {'min': 0, 'max': 0, 'mean': 0}
        
        last_update = df['timestamp'].max() if not df.empty else None
        
        return {
            'stats': stats,
            'chart_data': chart_data,
            'data_available': True,
            'last_update': last_update
        }
    except Exception as e:
        print(f"Errore nel caricamento o elaborazione dei dati: {e}")
        return {
            'stats': {},
            'chart_data': {},
            'data_available': False,
            'error': str(e)
        }

@app.route('/')
def index():
    # Ottieni i parametri di data se presenti
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    focused_sensor = request.args.get('focus', '')
    
    # Calcola le date predefinite
    today = datetime.now().date()
    date_ranges = {
        'today': today.isoformat(),
        'week': (today - timedelta(days=7)).isoformat(),
        'month': (today - timedelta(days=30)).isoformat()
    }
    
    # Processa i dati
    data = process_data(start_date, end_date)
    
    # Renderizza il template
    return render_template('index.html', 
                          sensors=SENSORS,
                          stats=data['stats'],
                          chart_data=data['chart_data'],
                          data_available=data['data_available'],
                          error=data.get('error', None),
                          date_ranges=date_ranges,
                          start_date=start_date or date_ranges['today'],
                          end_date=end_date or date_ranges['today'],
                          focused_sensor=focused_sensor,
                          last_update=data.get('last_update'))

if __name__ == '__main__':
    # Crea la directory templates se non esiste
    os.makedirs('templates', exist_ok=True)
    
    # Crea il template HTML
    with open('templates/index.html', 'w') as f:
        f.write("""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <title>Irrigo Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .chart-container {
            position: relative;
            height: 250px;
            width: 100%;
            margin-bottom: 20px;
        }
        .focus-container {
            position: relative;
            height: 400px;
            width: 100%;
        }
        .data-error {
            padding: 2rem;
            text-align: center;
        }
        body {
            padding-bottom: 2rem;
        }
    </style>
</head>
<body>
    <div class="container-fluid p-4">
        <h1 class="text-center mb-4">Irrigo Dashboard</h1>
        
        {% if data_available %}
            <!-- Debug info -->
            <div class="alert alert-info mb-3">
                <div class="row">
                    {% for sensor, sensor_stats in stats.items() %}
                    <div class="col-md-3 mb-2">
                        <div class="row align-items-center">
                            <div class="col-6">
                                <h4 class="mb-0">{{ "%.2f"|format(sensor_stats.current) }} <small>{{ sensors[sensor].unit }}</small></h4>
                                <small class="text-muted">{{ sensors[sensor].name }}</small>
                            </div>
                            <div class="col-6">
                                <div class="text-muted" style="font-size:0.8em">
                                    Min: {{ "%.2f"|format(sensor_stats.min) }} {{ sensors[sensor].unit }}<br>
                                    Max: {{ "%.2f"|format(sensor_stats.max) }} {{ sensors[sensor].unit }}<br>
                                    Media: {{ "%.2f"|format(sensor_stats.mean) }} {{ sensors[sensor].unit }}
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="mt-2 text-muted">
                    Ultimo aggiornamento: 
                    {% if last_update %}
                        {{ last_update.strftime('%Y-%m-%d %H:%M:%S') }}
                    {% else %}
                        Nessun dato disponibile
                    {% endif %}
                </div>
            </div>
            
            <!-- Controlli -->
            <form class="row mb-4" method="get" action="/">
                <div class="col-md-6">
                    <label class="form-label">Seleziona intervallo temporale:</label>
                    <div class="d-flex flex-wrap">
                        <input type="date" name="start_date" id="start-date" class="form-control me-2 mb-2" style="max-width: 200px;" value="{{ start_date }}">
                        <input type="date" name="end_date" id="end-date" class="form-control me-2 mb-2" style="max-width: 200px;" value="{{ end_date }}">
                        <input type="hidden" name="focus" id="focus-input" value="{{ focused_sensor }}">
                        <button type="submit" class="btn btn-primary me-2 mb-2">Filtra</button>
                        <button type="button" id="btn-home" class="btn btn-outline-primary me-2 mb-2">
                            <i class="bi bi-house-door"></i>
                        </button>
                        <button type="button" id="btn-today" class="btn btn-outline-primary me-2 mb-2">Oggi</button>
                        <button type="button" id="btn-week" class="btn btn-outline-primary me-2 mb-2">Ultima settimana</button>
                        <button type="button" id="btn-month" class="btn btn-outline-primary mb-2">Ultimo mese</button>
                    </div>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Focus su sensore:</label>
                    <select id="sensor-focus" class="form-select mb-2" style="max-width: 300px;">
                        <option value="">Tutti i sensori</option>
                        {% for id, sensor_info in sensors.items() %}
                            <option value="{{ id }}" {% if id == focused_sensor %}selected{% endif %}>{{ sensor_info.name }} ({{ sensor_info.unit }})</option>
                        {% endfor %}
                    </select>
                </div>
            </form>
            
            {% if focused_sensor and focused_sensor in sensors %}
                <!-- Grafico in focus -->
                <div class="mt-4">
                    <h3 class="mb-3">Focus su: {{ sensors[focused_sensor].name }} ({{ sensors[focused_sensor].unit }})</h3>
                    <div class="focus-container" id="chart-focus"></div>
                    <button id="btn-close-focus" class="btn btn-outline-secondary mt-2">Chiudi focus</button>
                </div>
            {% else %}
                <!-- Contenitore per i grafici -->
                <div class="row" id="graphs-container">
                    {% for sensor_id, sensor_name in sensors.items() %}
                        {% if sensor_id in chart_data %}
                            <div class="col-md-6 mb-4">
                                <div class="chart-container" id="chart-{{ sensor_id }}"></div>
                            </div>
                        {% endif %}
                    {% endfor %}
                </div>
            {% endif %}
            
        {% else %}
            <div class="alert alert-danger data-error">
                <h3>Errore durante il caricamento dei dati</h3>
                {% if error %}
                    <p>{{ error }}</p>
                {% else %}
                    <p>Nessun dato disponibile.</p>
                {% endif %}
            </div>
        {% endif %}
    </div>

    <script>
        const sensors = {{ sensors|tojson }};
        const chartData = {{ chart_data|tojson }};
        const dateRanges = {{ date_ranges|tojson }};
        const focusedSensor = "{{ focused_sensor }}";
        let charts = {};
        
        // Funzione per creare un grafico
        function createChart(containerId, sensorId, sensorName, isFocus = false) {
            const unit = sensors[sensorId].unit || '';
            const container = document.getElementById(containerId);
            if (!container) return;
            
            const data = chartData[sensorId];
            if (!data || data.timestamps.length === 0) {
                container.innerHTML = `<div class="alert alert-warning">Nessun dato valido per ${sensorName}</div>`;
                return;
            }
            
            // Crea canvas se non esiste
            let canvas = container.querySelector('canvas');
            if (!canvas) {
                canvas = document.createElement('canvas');
                container.innerHTML = '';
                container.appendChild(canvas);
            }
            
            // Crea configurazione grafico
            const chartConfig = {
                type: 'line',
                data: {
                    labels: data.timestamps,
                    datasets: [{
                        label: sensorName,
                        data: data.values,
                        borderColor: '#17a2b8',
                        borderWidth: 2,
                        pointRadius: isFocus ? 2 : 0,
                        pointHoverRadius: 5,
                        tension: 0.1,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 0 // Disabilita animazioni per performance
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: sensorName + ' (' + unit + ')',
                            font: {
                                size: 16
                            }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        },
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Data'
                            },
                            ticks: {
                                maxRotation: 45,
                                minRotation: 45,
                                maxTicksLimit: isFocus ? 10 : 6
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: sensorName + ' (' + unit + ')'
                            },
                            beginAtZero: false
                        }
                    }
                }
            };
            
            // Crea il grafico
            const chart = new Chart(canvas, chartConfig);
            charts[containerId] = chart;
        }
        
        // Configurazione date picker
        function setupDatePickers() {
            document.getElementById('btn-home').addEventListener('click', (e) => {
                e.preventDefault();
                window.location.href = '/'; // Resetta tutti i filtri
            });
            
            document.getElementById('btn-today').addEventListener('click', (e) => {
                e.preventDefault();
                document.getElementById('start-date').value = dateRanges.today;
                document.getElementById('end-date').value = dateRanges.today;
                document.querySelector('form').submit();
            });
            
            document.getElementById('btn-week').addEventListener('click', (e) => {
                e.preventDefault();
                document.getElementById('start-date').value = dateRanges.week;
                document.getElementById('end-date').value = dateRanges.today;
                document.querySelector('form').submit();
            });
            
            document.getElementById('btn-month').addEventListener('click', (e) => {
                e.preventDefault();
                document.getElementById('start-date').value = dateRanges.month;
                document.getElementById('end-date').value = dateRanges.today;
                document.querySelector('form').submit();
            });
        }
        
        // Funzione per gestire il focus selector
        function setupFocusSelector() {
            const focusSelector = document.getElementById('sensor-focus');
            if (focusSelector) {
                focusSelector.addEventListener('change', () => {
                    document.getElementById('focus-input').value = focusSelector.value;
                    document.querySelector('form').submit();
                });
            }
            
            const closeBtn = document.getElementById('btn-close-focus');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    document.getElementById('focus-input').value = '';
                    document.querySelector('form').submit();
                });
            }
        }
        
        
        // Inizializzazione all'avvio della pagina
        document.addEventListener('DOMContentLoaded', () => {
            if (focusedSensor && chartData[focusedSensor]) {
                createChart('chart-focus', focusedSensor, sensors[focusedSensor].name, true);
            } else {
                for (const [sensorId, sensorInfo] of Object.entries(sensors)) {
                    if (chartData[sensorId]) {
                        createChart(`chart-${sensorId}`, sensorId, sensorInfo.name);
                    }
                }
            }
            
            setupDatePickers();
            setupFocusSelector();
        });
    </script>
</body>
</html>""")
    
    # Jinja2 filter per la data corrente
    @app.template_filter('now')
    def template_now(format='%Y-%m-%d\n%H:%M:%S'):
        return datetime.now().strftime(format)
    
    # Avvio dell'applicazione con modalità debug disabilitata
    app.run(debug=False, host='0.0.0.0', port=8050, threaded=False)
