import os
import flask
import pandas as pd
import numpy as np
from dash import Dash, html, dcc, callback, Input, Output, State, callback_context, no_update
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Inizializzazione del server Flask
server = flask.Flask(__name__)

@server.route('/')
def index():
    return flask.redirect('/dash/')

# Inizializzazione dell'applicazione Dash
app = Dash(
    __name__,
    server=server,
    routes_pathname_prefix='/dash/',
    external_stylesheets=['https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css'],
    suppress_callback_exceptions=True
)

# Definizione dei sensori da visualizzare
SENSORS = {
    'pressure': 'Pressione',
    'temperature': 'Temperatura',
    'humidity': 'Umidità',
    'env_pressure': 'Pressione Ambientale'
}

# Funzione per caricare i dati dal file CSV
def load_data():
    csv_path = os.path.expanduser('~/telemetria.csv')
    try:
        df = pd.read_csv(csv_path)
        
        # Converti timestamp in datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Converti tutte le colonne dei sensori a float
        for sensor in SENSORS.keys():
            if sensor in df.columns:
                df[sensor] = pd.to_numeric(df[sensor], errors='coerce')
        
        # Ordina per timestamp
        df = df.sort_values('timestamp')
        return df
    except Exception as e:
        print(f"Errore caricamento CSV: {e}")
        return pd.DataFrame()

# Funzione per creare un grafico per un sensore specifico
def create_sensor_graph(df, sensor_id, sensor_name, is_focused=False):
    if df.empty or sensor_id not in df.columns:
        return go.Figure().update_layout(title=f"Nessun dato disponibile per {sensor_name}")
    
    # L'altezza è ora controllata dal contenitore esterno, non dal grafico
    # height = 400 if is_focused else 250
    
    # Estrai esplicitamente i dati come liste Python per evitare problemi di indice
    x_values = df['timestamp'].tolist()
    y_values = df[sensor_id].tolist()
    
    # Log per debug
    print(f"Creazione grafico per {sensor_name}")
    print(f"Numero di valori X: {len(x_values)}")
    print(f"Numero di valori Y: {len(y_values)}")
    if len(y_values) > 0:
        print(f"Esempio primi 3 valori Y: {y_values[:3]}")
    
    # IMPORTANTE: Usa go.Figure e go.Scatter direttamente per avere controllo totale
    fig = go.Figure()
    
    # Aggiungi la traccia con i dati espliciti X e Y
    fig.add_trace(
        go.Scatter(
            x=x_values,       # Usa la lista esplicita dei timestamp
            y=y_values,       # Usa la lista esplicita dei valori
            mode='lines',     # Tipo di visualizzazione: linee
            line=dict(color='#17a2b8', width=2),
            name=sensor_name
        )
    )
    
    # Calcola il range Y basato sui dati effettivi
    if y_values:
        valid_y_values = [y for y in y_values if y is not None and not np.isnan(y)]
        if valid_y_values:
            min_y = min(valid_y_values)
            max_y = max(valid_y_values)
            padding = (max_y - min_y) * 0.1 if max_y > min_y else 1
            y_range = [min_y - padding, max_y + padding]
        else:
            y_range = [0, 1]  # Default se non ci sono dati validi
    else:
        y_range = [0, 1]  # Default se non ci sono dati
    
    # Impostazioni di layout con range Y fisso e senza specificare altezza
    fig.update_layout(
        title=sensor_name,
        # Rimuove height per adattarsi al contenitore
        margin=dict(l=40, r=20, t=40, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        hovermode='x unified',
        transition_duration=0,  # Disabilita animazioni
        uirevision='constant',  # Mantiene lo stato del grafico tra gli aggiornamenti
        autosize=True,         # Permette al grafico di adattarsi al contenitore
    )
    
    # Impostazioni asse X
    fig.update_xaxes(
        title='Ora',
        showgrid=True,
        gridwidth=1,
        gridcolor='#eeeeee',
        tickformat='%Y-%m-%d\n%H:%M:%S'
    )
    
    # Impostazioni asse Y con range FISSO
    fig.update_yaxes(
        title=sensor_name,
        showgrid=True,
        gridwidth=1,
        gridcolor='#eeeeee',
        zeroline=True,
        range=y_range,          # Imposta un range fisso basato sui dati
        fixedrange=False,       # Permette zoom manuale
        autorange=False,        # Disabilita autorange per impedire il crescere automatico
    )
    
    return fig

# Layout dell'applicazione
app.layout = html.Div(className='container-fluid p-4', style={'height': '100vh', 'overflowY': 'auto'}, children=[
    html.H1("Dashboard Telemetria", className='text-center mb-4'),
    
    # Visualizzazione di debug
    html.Div(id='debug-info', className='alert alert-info mb-3'),
    
    # Controlli
    html.Div(className='row mb-4', children=[
        # Selettore intervallo temporale
        html.Div(className='col-md-6', children=[
            html.Label("Seleziona intervallo temporale:", className='form-label'),
            html.Div(className='d-flex flex-wrap', children=[
                dcc.DatePickerRange(
                    id='date-range',
                    className='me-2 mb-2',
                    display_format='DD/MM/YYYY',
                    start_date_placeholder_text='Data inizio',
                    end_date_placeholder_text='Data fine',
                    clearable=True,
                ),
                html.Button('Oggi', id='btn-today', className='btn btn-outline-primary me-2 mb-2'),
                html.Button('Ultima settimana', id='btn-week', className='btn btn-outline-primary me-2 mb-2'),
                html.Button('Ultimo mese', id='btn-month', className='btn btn-outline-primary mb-2')
            ])
        ]),
        
        # Selettore sensore per focus
        html.Div(className='col-md-6', children=[
            html.Label("Focus su sensore:", className='form-label'),
            dcc.Dropdown(
                id='sensor-focus',
                options=[{'label': name, 'value': id} for id, name in SENSORS.items()],
                placeholder='Tutti i sensori',
                clearable=True,
                style={'width': '100%'}
            )
        ])
    ]),
    
    # Contenitore per i grafici con altezza fissa e scroll interno
    html.Div(id='graphs-container', className='row', style={'minHeight': '400px', 'maxHeight': '1200px'}),
    
    # Grafico in focus (quando selezionato) con altezza fissa
    html.Div(id='focus-container', className='mt-4', style={'minHeight': '100px', 'maxHeight': '600px'}),
    
    # Intervallo di aggiornamento
    dcc.Interval(id='interval-update', interval=60*1000, n_intervals=0),
    
    # Store per i dati
    dcc.Store(id='telemetry-data')
])

# Callback per caricare i dati e mostrare debug info
@callback(
    [Output('telemetry-data', 'data'),
     Output('debug-info', 'children')],
    Input('interval-update', 'n_intervals')
)
def update_data(n):
    df = load_data()
    
    # Info di debug
    debug_info = []
    if not df.empty:
        for sensor in SENSORS.keys():
            if sensor in df.columns:
                # Calcola statistiche solo se ci sono valori validi
                if not df[sensor].isna().all():
                    stats = {
                        'min': float(df[sensor].min()),
                        'max': float(df[sensor].max()),
                        'media': float(df[sensor].mean())
                    }
                    debug_info.append(html.Div(f"{SENSORS[sensor]}: Min={stats['min']:.2f}, Max={stats['max']:.2f}, Media={stats['media']:.2f}"))
        
        # Converti per storage
        data_json = df.to_json(date_format='iso', orient='split')
        return data_json, debug_info
    else:
        return None, html.Div("Nessun dato caricato", className="text-danger")

# Callback per i pulsanti di intervallo temporale
@callback(
    [Output('date-range', 'start_date'),
     Output('date-range', 'end_date')],
    [Input('btn-today', 'n_clicks'),
     Input('btn-week', 'n_clicks'),
     Input('btn-month', 'n_clicks')],
    prevent_initial_call=True
)
def update_date_range(today_clicks, week_clicks, month_clicks):
    ctx = callback_context
    if not ctx.triggered:
        return [None, None]
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    today = datetime.now().date()
    
    if button_id == 'btn-today':
        return [today, today]
    elif button_id == 'btn-week':
        return [today - timedelta(days=7), today]
    elif button_id == 'btn-month':
        return [today - timedelta(days=30), today]
    
    return [None, None]

# Callback per visualizzare tutti i grafici
@callback(
    Output('graphs-container', 'children'),
    [Input('telemetry-data', 'data'),
     Input('date-range', 'start_date'),
     Input('date-range', 'end_date'),
     Input('sensor-focus', 'value')]
)
def update_all_graphs(data, start_date, end_date, focused_sensor):
    if not data:
        return [html.Div("Nessun dato disponibile", className='col-12 text-center p-5')]
    
    try:
        # Carica dati dallo store
        df = pd.read_json(data, orient='split')
        
        # Assicurati che timestamp sia datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Filtra per intervallo di date se specificato
        if start_date and end_date:
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date) + timedelta(days=1) - timedelta(seconds=1)
            df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        
        # Se c'è un sensore in focus, non mostrare i grafici qui
        if focused_sensor:
            return []
        
        # Crea un grafico per ogni sensore
        graphs = []
        for sensor_id, sensor_name in SENSORS.items():
            if sensor_id in df.columns:
                # Filtra righe con valori validi per questo sensore
                sensor_df = df.dropna(subset=[sensor_id]).copy()
                
                if not sensor_df.empty:
                    # Print per debug
                    print(f"Dati per grafico {sensor_name}:")
                    print(f"Numero di righe: {len(sensor_df)}")
                    if len(sensor_df) > 0:
                        print(f"Esempio primi 3 valori: {sensor_df[sensor_id].head(3).tolist()}")
                    
                    # Impostazione delle dimensioni fisse del grafico
                    graphs.append(html.Div(className='col-md-6 mb-4', style={'height': '300px'}, children=[
                        dcc.Graph(
                            id={'type': 'sensor-graph', 'index': sensor_id},
                            figure=create_sensor_graph(sensor_df, sensor_id, sensor_name),
                            config={
                                'displayModeBar': True,
                                'scrollZoom': True  # Abilita zoom con scroll
                            },
                            style={'height': '100%'}  # Forza l'altezza del grafico
                        )
                    ]))
                else:
                    graphs.append(html.Div(className='col-md-6 mb-4', style={'height': '300px'}, children=[
                        html.Div(f"Nessun dato valido per {sensor_name}", className='alert alert-warning p-3')
                    ]))
        
        return graphs
    
    except Exception as e:
        print(f"Errore nell'aggiornamento dei grafici: {e}")
        import traceback
        traceback.print_exc()
        return [html.Div(f"Errore nell'elaborazione dei dati: {str(e)}", className='col-12 alert alert-danger')]

# Callback per il grafico in focus
@callback(
    Output('focus-container', 'children'),
    [Input('telemetry-data', 'data'),
     Input('date-range', 'start_date'),
     Input('date-range', 'end_date'),
     Input('sensor-focus', 'value')]
)
def update_focus_graph(data, start_date, end_date, focused_sensor):
    if not data or not focused_sensor:
        return []
    
    try:
        # Carica dati dallo store
        df = pd.read_json(data, orient='split')
        
        # Assicurati che timestamp sia datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Filtra per intervallo di date se specificato
        if start_date and end_date:
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date) + timedelta(days=1) - timedelta(seconds=1)
            df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        
        # Verifica che il sensore sia nei dati
        if focused_sensor in df.columns:
            # Filtra righe con valori validi per questo sensore
            sensor_df = df.dropna(subset=[focused_sensor]).copy()
            
            if not sensor_df.empty:
                # Print per debug
                print(f"Focus su {SENSORS[focused_sensor]}:")
                print(f"Numero di righe: {len(sensor_df)}")
                if len(sensor_df) > 0:
                    print(f"Esempio primi 3 valori: {sensor_df[focused_sensor].head(3).tolist()}")
                
                return [
                    html.H3(f"Focus su: {SENSORS[focused_sensor]}", className='mb-3'),
                    html.Div(style={'height': '500px'}, children=[
                        dcc.Graph(
                            id='focus-graph',
                            figure=create_sensor_graph(sensor_df, focused_sensor, SENSORS[focused_sensor], is_focused=True),
                            config={
                                'displayModeBar': True,
                                'scrollZoom': True  # Abilita zoom con scroll
                            },
                            style={'height': '100%'}  # Imposta altezza al 100% del contenitore
                        )
                    ]),
                    html.Button(
                        'Chiudi focus', 
                        id='btn-close-focus',
                        className='btn btn-outline-secondary mt-2',
                        n_clicks=0
                    )
                ]
            else:
                return [html.Div(f"Nessun dato valido per {SENSORS[focused_sensor]}", className='alert alert-warning')]
        else:
            return [html.Div(f"Sensore {SENSORS[focused_sensor]} non trovato nei dati", className='alert alert-warning')]
    
    except Exception as e:
        print(f"Errore nell'aggiornamento del focus: {e}")
        import traceback
        traceback.print_exc()
        return [html.Div(f"Errore nell'elaborazione dei dati: {str(e)}", className='alert alert-danger')]

# Callback per chiudere il focus
@callback(
    Output('sensor-focus', 'value'),
    Input('btn-close-focus', 'n_clicks'),
    prevent_initial_call=True
)
def close_focus(n_clicks):
    if n_clicks > 0:
        return None
    return no_update

# Avvio dell'applicazione
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)