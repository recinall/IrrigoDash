import os
import flask
import pandas as pd
from dash import Dash, html, dcc, callback, Input, Output, State, callback_context, no_update
import plotly.express as px
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
    external_stylesheets=['https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css']
)

# Funzione per caricare i dati dal file CSV
def load_data():
    csv_path = os.path.expanduser('~/telemetria.csv')
    try:
        df = pd.read_csv(csv_path)
        # Converti timestamp in datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Ordina per timestamp
        df = df.sort_values('timestamp')
    except Exception as e:
        print(f"Errore caricamento CSV: {e}")
        df = pd.DataFrame()
    return df

# Definizione dei sensori da visualizzare
SENSORS = {
    'pressure': 'Pressione',
    'temperature': 'Temperatura',
    'humidity': 'Umidità',
    'env_pressure': 'Pressione Ambientale'
}

# Funzione per creare un grafico per un sensore specifico
def create_sensor_graph(df, sensor_id, sensor_name, is_focused=False):
    if df.empty or sensor_id not in df.columns:
        return go.Figure().update_layout(title=f"Nessun dato disponibile per {sensor_name}")
    
    height = 400 if is_focused else 250
    
    # Assicuriamoci che i dati siano validi
    valid_df = df[['timestamp', sensor_id]].dropna()
    
    fig = px.line(
        valid_df,
        x='timestamp',
        y=sensor_id,
        title=sensor_name,
        labels={sensor_id: 'Valore', 'timestamp': 'Ora'},
        color_discrete_sequence=['#17a2b8']
    )
    
    fig.update_layout(
        height=height,
        transition_duration=500,
        plot_bgcolor='white',
        margin={'t': 40, 'l': 40, 'r': 20, 'b': 40},
        hovermode='x unified'
    )
    
    fig.update_xaxes(
        title_text='Ora',
        showgrid=True, 
        gridwidth=1, 
        gridcolor='#eeeeee'
    )
    
    fig.update_yaxes(
        title_text='Valore',
        showgrid=True, 
        gridwidth=1, 
        gridcolor='#eeeeee'
    )
    
    return fig

# Layout dell'applicazione
app.layout = html.Div(className='container-fluid p-4', children=[
    html.H1("Dashboard Telemetria", className='text-center mb-4'),
    
    # Controlli
    html.Div(className='row mb-4', children=[
        # Selettore intervallo temporale
        html.Div(className='col-md-6', children=[
            html.Label("Seleziona intervallo temporale:", className='form-label'),
            html.Div(className='d-flex', children=[
                dcc.DatePickerRange(
                    id='date-range',
                    className='me-2',
                    display_format='DD/MM/YYYY',
                    start_date_placeholder_text='Data inizio',
                    end_date_placeholder_text='Data fine',
                    clearable=True,
                ),
                html.Button('Oggi', id='btn-today', className='btn btn-outline-primary me-2'),
                html.Button('Ultima settimana', id='btn-week', className='btn btn-outline-primary me-2'),
                html.Button('Ultimo mese', id='btn-month', className='btn btn-outline-primary')
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
    
    # Contenitore per i grafici
    html.Div(id='graphs-container', className='row'),
    
    # Grafico in focus (quando selezionato)
    html.Div(id='focus-container', className='mt-4'),
    
    # Intervallo di aggiornamento
    dcc.Interval(id='interval-update', interval=60*1000, n_intervals=0),
    
    # Store per i dati
    dcc.Store(id='telemetry-data')
])

# Callback per caricare i dati
@callback(
    Output('telemetry-data', 'data'),
    Input('interval-update', 'n_intervals')
)
def update_data(n):
    df = load_data()
    if not df.empty:
        return df.to_json(date_format='iso', orient='split')
    return None

# Callback per i pulsanti di intervallo temporale
@callback(
    [Output('date-range', 'start_date'),
     Output('date-range', 'end_date')],
    [Input('btn-today', 'n_clicks'),
     Input('btn-week', 'n_clicks'),
     Input('btn-month', 'n_clicks')],
    [State('telemetry-data', 'data')],
    prevent_initial_call=True
)
def update_date_range(today_clicks, week_clicks, month_clicks, data):
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
    
    df = pd.read_json(data, orient='split')
    
    # Filtra per intervallo di date se specificato
    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date) + timedelta(days=1) - timedelta(seconds=1)  # Fine della giornata
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
    
    # Se c'è un sensore in focus, non mostrare i grafici qui
    if focused_sensor:
        return []
    
    # Crea un grafico per ogni sensore
    graphs = []
    for sensor_id, sensor_name in SENSORS.items():
        graphs.append(html.Div(className='col-md-6 mb-4', children=[
            dcc.Graph(
                id={'type': 'sensor-graph', 'index': sensor_id},
                figure=create_sensor_graph(df, sensor_id, sensor_name)
            )
        ]))
    
    return graphs

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
    
    df = pd.read_json(data, orient='split')
    
    # Filtra per intervallo di date se specificato
    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date) + timedelta(days=1) - timedelta(seconds=1)  # Fine della giornata
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
    
    return [
        html.H3(f"Focus su: {SENSORS[focused_sensor]}", className='mb-3'),
        dcc.Graph(
            id='focus-graph',
            figure=create_sensor_graph(df, focused_sensor, SENSORS[focused_sensor], is_focused=True)
        ),
        html.Button(
            'Chiudi focus', 
            id='btn-close-focus', 
            className='btn btn-outline-secondary mt-2',
            n_clicks=0
        )
    ]

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
