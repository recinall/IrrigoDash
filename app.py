import os
import flask
import pandas as pd
from dash import Dash, html, dcc, callback, Input, Output
import plotly.express as px

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
        # Trasformazione da wide a long format
        df = df.melt(
            id_vars=['timestamp', 'pumpRunning', 'outputValveOpen'],
            var_name='sensor',
            value_name='value'
        )
    except Exception as e:
        print(f"Errore caricamento CSV: {e}")
        df = pd.DataFrame()
    return df

# Layout dell'applicazione
app.layout = html.Div(className='container p-4', children=[
    html.H1("Dashboard Telemetria", className='text-center mb-4'),
    dcc.Dropdown(
        id='sensor-dropdown',
        placeholder='Seleziona sensore...',
        style={'width': '50%', 'margin': 'auto'}
    ),
    dcc.Graph(id='telemetry-graph'),
    dcc.Interval(id='interval-update', interval=60*1000, n_intervals=0)
])

# Callback per aggiornare il menu a tendina
@callback(
    Output('sensor-dropdown', 'options'),
    Input('interval-update', 'n_intervals')
)
def update_dropdown(n):
    return [
        {'label': 'Pressione', 'value': 'pressure'},
        {'label': 'Temperatura', 'value': 'temperature'},
        {'label': 'Umidità', 'value': 'humidity'},
        {'label': 'Pressione Ambientale', 'value': 'env_pressure'}
    ]

# Callback per aggiornare il grafico
@callback(
    Output('telemetry-graph', 'figure'),
    Input('sensor-dropdown', 'value'),
    Input('interval-update', 'n_intervals')
)
def update_graph(selected_sensor, n):
    df = load_data()
    
    if df.empty or not selected_sensor:
        return px.line(title="Seleziona un sensore dal menu")
    
    dff = df[df['sensor'] == selected_sensor]
    
    try:
        dff['timestamp'] = pd.to_datetime(dff['timestamp'])
        fig = px.line(
            dff,
            x='timestamp',
            y='value',
            title=f"Andamento {selected_sensor}",
            labels={'value': 'Valore', 'timestamp': 'Ora'},
            color_discrete_sequence=['#17a2b8']
        )
    except Exception as e:
        print(f"Errore generazione grafico: {e}")
        return px.line(title="Errore nei dati")
    
    fig.update_layout(
        transition_duration=500,
        plot_bgcolor='white',
        margin={'t': 40},
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

# Avvio dell'applicazione
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
