from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import jwt
from datetime import datetime, timedelta, timezone
import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SECRET_KEY'] = 'aywuit98723hsiddufhg'  # JWT Token

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ✅ User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    mobile = db.Column(db.String(10), unique=True, nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'farmer' or 'admin'

    def __init__(self, username, email, password, name, mobile, role):
        self.username = username
        self.email = email
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
        self.name = name
        self.mobile = mobile
        self.role = role

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)


with app.app_context():
    db.create_all()

# Load the dataset
df = pd.read_csv('kisaan.csv')

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/home')
def home_page():
    return render_template("index.html")

@app.route('/about')
def about():
    return render_template('about.html')

# ✅ Signup Page Route
@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template("signup.html")


# ✅ Sign Up API
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    mobile = data.get('phone')
    role = data.get('role')

    if not all([username, email, password, name, mobile, role]):
        return jsonify({"error": "All fields are required"}), 400

    if role not in ["User", "admin"]:
        return jsonify({"error": "Invalid role"}), 400

    # ✅ Check if user already exists
    existing_user = User.query.filter(
        (User.email == email) | (User.username == username) | (User.mobile == mobile)
    ).first()
    
    if existing_user:
        return jsonify({"error": "User with this email, username, or mobile already exists"}), 400

    # ✅ Create new user
    new_user = User(username, email, password, name, mobile, role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


# ✅ Login Page Route
@app.route('/login', methods=['GET'])
def login_page():
    return render_template("login.html")


# ✅ Login API
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # ✅ Validate Inputs
    if not email or not password:
        return jsonify({"error": "Both email/mobile and password are required"}), 400

    # ✅ Fetch User from DB
    user = User.query.filter((User.email == email) | (User.mobile == email)).first()

    if user and user.check_password(password):
        # ✅ Generate JWT Token
        token_payload = {
            "user_id": user.id,
            "role": user.role,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        token = jwt.encode(token_payload, app.config["SECRET_KEY"], algorithm="HS256")

        return jsonify({"token": token, "role": user.role}), 200

    return jsonify({"error": "Invalid email, mobile, or password"}), 401


#Graphs function
def most_affected_crops():
    fig1 = go.Figure()
    top_crops = df['Crop'].value_counts().nlargest(10).reset_index()
    top_crops.columns = ['Crop', 'Count']

    fig1 = px.bar(
        top_crops,
        x='Crop',
        y='Count',
        title='🌾 Most Affected Crops by Grievances',
        labels={'Crop': 'Crop', 'Count': 'Number of Grievances'},
        color='Count',
        color_continuous_scale='YlGn',
        template='plotly_dark',
    )
    graph1_html = pio.to_html(fig1, full_html=False)
    return graph1_html

def crop_category_distribution():
    fig2 = go.Figure()
    fig2 = px.pie(
    df,
    names='Category',
    title='🍎 Crop Category Distribution (Fruits, Cereals, Pulses...)',
    hole=0.4,
    color_discrete_sequence=px.colors.qualitative.Pastel
    )
    graph2_html = pio.to_html(fig2, full_html=False)
    return graph2_html

def crop_vs_sector_heatmap():
    fig3 = go.Figure()
    crop_sector = df.groupby(['Crop', 'Sector']).size().reset_index(name='Count')

    fig3 = px.density_heatmap(
        crop_sector,
        x='Sector',
        y='Crop',
        z='Count',
        title='🔥 Crop vs Sector Heatmap',
        color_continuous_scale='YlOrRd'
    )
    graph3_html = pio.to_html(fig3, full_html=False)
    return graph3_html

def generate_insights_graph():
    global df
    fig4 = go.Figure()
    df = df.dropna(subset=['QueryType', 'KccAns'])

    # Assign resolution based on KccAns content
    df['ResolutionStatus'] = df['KccAns'].apply(lambda x: 'Resolved' if 'solved' in x.lower() or 'provided' in x.lower() else 'Unresolved')

    # Create a new column for scheme
    df['Scheme'] = 'KCC'

    # Keep only top 10 query types for readability
    top_queries = df['QueryType'].value_counts().nlargest(10).index
    df['QueryType'] = df['QueryType'].apply(lambda x: x if x in top_queries else 'Other')

    # Create label list and mapping
    labels = list(df['QueryType'].unique()) + list(df['Scheme'].unique()) + list(df['ResolutionStatus'].unique())
    label_map = {label: i for i, label in enumerate(labels)}

    # QueryType → Scheme
    source = []
    target = []
    value = []

    group_1 = df.groupby(['QueryType', 'Scheme']).size().reset_index(name='Count')
    for _, row in group_1.iterrows():
        source.append(label_map[row['QueryType']])
        target.append(label_map[row['Scheme']])
        value.append(row['Count'])

    # Scheme → Resolution
    group_2 = df.groupby(['Scheme', 'ResolutionStatus']).size().reset_index(name='Count')
    for _, row in group_2.iterrows():
        source.append(label_map[row['Scheme']])
        target.append(label_map[row['ResolutionStatus']])
        value.append(row['Count'])

    # Define custom node colors
    node_colors = ['#6AB187'] * len(df['QueryType'].unique()) + ['#4A90E2'] + ['#F5A623', '#D0021B']

    # Plot the Sankey diagram
    fig4 = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20,
            thickness=20,
            line=dict(color="gray", width=0.5),
            label=labels,
            color=node_colors
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color=["rgba(106, 177, 135, 0.4)"] * len(group_1) + ["rgba(255, 165, 0, 0.4)"] * len(group_2)
        )
    )])

    fig4.update_layout(
        title_text="QueryType → Scheme (KCC) → Resolution Flow",
        font_size=13,
        height=650
    )
    graph4_html = pio.to_html(fig4, full_html=False)
    return graph4_html




def total_grevience_count():
    fig51 = go.Figure()
    fig51.add_trace(go.Indicator(
        mode="number",
        value=len(df),
        title={
            "text": "📌 Total Grievances",
            "font": {
                "size": 16,
                "color": "#ffffff",
                "family": "Arial, sans-serif"
            }
        },
        number={
            "font": {
                "size": 40,
                "color": "#00cec9",
                "family": "Arial, sans-serif"
            },
            "prefix": "",
            "suffix": ""
        },
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    
    # Update layout to fit the stat card
    fig51.update_layout(
        height=100,
        width=200,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=20, b=10)
    )
    
    graph51_html = pio.to_html(fig51, full_html=False)
    return graph51_html

def monthly_trends():
    fig52 = go.Figure()

    # Convert CreatedOn to datetime if not already
    df['CreatedOn'] = pd.to_datetime(df['CreatedOn'], errors='coerce')
    
    # Extract month and year from CreatedOn
    df['Month'] = df['CreatedOn'].dt.strftime('%Y-%m')
    
    # Get monthly counts and sort by date
    monthly_trend = df['Month'].value_counts().sort_index()
    
    fig52 = px.line(
        x=monthly_trend.index,
        y=monthly_trend.values,
        labels={'x': 'Month', 'y': 'Number of Grievances'},
        title='📈 Monthly Trend of Farmer Queries'
    )
    
    # Rotate x-axis labels for better readability
    fig52.update_xaxes(tickangle=45)
    
    graph52_html = pio.to_html(fig52, full_html=False)
    return graph52_html

def State_wise_Grievance_Distribution():
    fig53 = go.Figure()
    top_states = df['StateName'].value_counts().nlargest(10).reset_index()
    top_states.columns = ['State', 'Count']  # Rename columns for clarity

    fig53 = px.bar(
        top_states,
        x='State', y='Count',  # Use the renamed columns
        labels={'State': 'State', 'Count': 'Number of Grievances'},
        title='🏙️ Top 10 States by Grievances',
        color='Count'  # Optional: Color by count
    )
    graph53_html = pio.to_html(fig53, full_html=False)
    return graph53_html

def Sector_wise_Complaint_Share():
    fig54 = go.Figure()
    fig54 = px.pie(
    df,
    names='Sector',
    title='📊 Sector-wise Grievance Share',
    hole=0.4,
    color_discrete_sequence=px.colors.qualitative.Pastel
)
    graph54_html = pio.to_html(fig54, full_html=False)
    return graph54_html


def Query_Type_Frequency():
    fig6 = go.Figure()
    querytype_counts = df['QueryType'].value_counts().reset_index()
    querytype_counts.columns = ['QueryType', 'Count']
    fig6 = px.bar(
        querytype_counts,
        x='QueryType',
        y='Count',
        title='📋 Query Type Frequency',
        labels={'QueryType': 'Query Type', 'Count': 'Number of Queries'},
        color='Count',
        color_continuous_scale='Blues'
    )
    graph6_html = pio.to_html(fig6, full_html=False)
    return graph6_html

def QueryType_vs_State_Distribution():
    fig7 = go.Figure()
    query_state = df.groupby(['QueryType', 'StateName']).size().reset_index(name='Count')
    fig7 = px.density_heatmap(
    query_state,
    x='StateName',
    y='QueryType',
    z='Count',
    title='🗺️ Query Type vs State Distribution',
    color_continuous_scale='Viridis')
    graph7_html = pio.to_html(fig7, full_html=False)
    return graph7_html
    
    
def Top_10_Districts_with_Most_Grievances():
    fig8 = go.Figure()
    top_districts = df['DistrictName'].value_counts().nlargest(10)

    fig8 = px.bar(
        top_districts.sort_values(), 
        x=top_districts.values, 
        y=top_districts.index, 
        orientation='h',
        labels={'x': 'Number of Grievances', 'y': 'District'},
        title='🏙️ Top 10 Districts with Most Grievances',
        color=top_districts.values,
        color_continuous_scale='Oranges'
    )
    graph8_html = pio.to_html(fig8, full_html=False)
    return graph8_html

def District_wise_Grievance():
    fig81 = go.Figure()
    district_state = df.groupby(['StateName', 'DistrictName']).size().reset_index(name='Count')

    fig81 = px.density_heatmap(
        district_state,
        x='StateName',
        y='DistrictName',
        z='Count',
        title='🗺️ District-wise Grievance Heatmap',
        color_continuous_scale='Blues'
    )
    graph81_html = pio.to_html(fig81, full_html=False)
    return graph81_html

def Treemap_District_Sector():
    fig82 = go.Figure()
    fig82 = px.treemap(
    df,
    path=['DistrictName', 'Sector'],
    title='🌲 Treemap: District → Sector',
    color_discrete_sequence=px.colors.qualitative.Set3
)
    graph82_html = pio.to_html(fig82, full_html=False)
    return graph82_html


def Resolved_vs_Unresolved():
    global df
    fig9 = go.Figure()
    df['ResolutionStatus'] = df['KccAns'].apply(
        lambda x: 'Resolved' if isinstance(x, str) and ('solved' in x.lower() or 'provided' in x.lower()) else 'Unresolved'
    )
    fig_resolution_pie = px.pie(
    df,
    names='ResolutionStatus',
    title='🧾 Resolution Status of Grievances',
    hole=0.4,
    color_discrete_sequence=px.colors.qualitative.Set2
    )
    graph9_html = pio.to_html(fig_resolution_pie, full_html=False)
    return graph9_html

def Region_wise_Resolution_Comparison():
    fig91 = go.Figure()
    region_resolution = df.groupby(['StateName', 'ResolutionStatus']).size().reset_index(name='Count')

    fig91 = px.bar(
        region_resolution,
        x='StateName',
        y='Count',
        color='ResolutionStatus',
        title='📊 Region-wise Resolution Comparison',
        barmode='stack',
        labels={'StateName': 'State', 'Count': 'Number of Grievances'},
        color_discrete_sequence=px.colors.qualitative.Set1
    )
    graph91_html = pio.to_html(fig91, full_html=False)
    return graph91_html

def Monthly_Query_Trend():
    fig10 = go.Figure()
    
    # Convert CreatedOn to datetime if not already
    df['CreatedOn'] = pd.to_datetime(df['CreatedOn'], errors='coerce')
    
    # Extract month and year from CreatedOn
    df['Month'] = df['CreatedOn'].dt.strftime('%Y-%m')
    
    # Get monthly counts and sort by date
    monthly_trend = df['Month'].value_counts().sort_index()
    
    fig10 = px.line(
        x=monthly_trend.index,
        y=monthly_trend.values,
        labels={'x': 'Month', 'y': 'Number of Queries'},
        title='📅 Monthly Query Trend'
    )
    
    # Rotate x-axis labels for better readability
    fig10.update_xaxes(tickangle=45)
    
    graph10_html = pio.to_html(fig10, full_html=False)
    return graph10_html

def Yearly_Trend_Breakdown():
    fig11 = go.Figure()
    
    # Ensure 'Year' and 'Month_Num' columns exist and are numeric
    df['Year'] = pd.to_datetime(df['CreatedOn'], errors='coerce').dt.year
    df['Month_Num'] = pd.to_datetime(df['CreatedOn'], errors='coerce').dt.month

    # Group data by Year and Month_Num
    year_month = df.groupby(['Year', 'Month_Num']).size().reset_index(name='Count')

    # Create the line plot
    fig11 = px.line(
        year_month,
        x='Month_Num',
        y='Count',
        color='Year',
        title='📈 Yearly Trend Breakdown (Month-wise)',
        labels={'Month_Num': 'Month', 'Count': 'Number of Queries'}
    )
    
    # Convert the plot to HTML
    graph11_html = pio.to_html(fig11, full_html=False)
    return graph11_html







#Analysis Pages

@app.route('/crop-analysis')
def crop_analysis():
    graph1 = most_affected_crops()
    graph2 = crop_category_distribution()
    graph3 = crop_vs_sector_heatmap()
    return render_template("crop_analysis.html",graph1=graph1,graph2=graph2,graph3=graph3)


@app.route('/insights')
def insights():
    graph4 = generate_insights_graph()
    return render_template("insights.html", graph4=graph4)


@app.route('/overview')
def overview():
    
    graph51 = total_grevience_count()
    graph52 = monthly_trends()
    graph53 = State_wise_Grievance_Distribution()
    graph54 = Sector_wise_Complaint_Share()
    return render_template("overview.html",graph51=graph51,graph52=graph52,graph53=graph53,graph54=graph54)

@app.route('/query-type')
def query_Type():
    graph6 = Query_Type_Frequency()
    graph7 = QueryType_vs_State_Distribution()

    return render_template("query_type.html",graph6=graph6,graph7=graph7)

@app.route('/region-analysis')
def region_analysis():
    graph8 = Top_10_Districts_with_Most_Grievances()
    graph81 = District_wise_Grievance()
    graph82 = Treemap_District_Sector()

    return render_template("region_analysis.html",graph8=graph8,graph81=graph81,graph82=graph82)

@app.route('/resolution-insights')
def resolution_insights():
    graph9 = Resolved_vs_Unresolved()
    graph91 = Region_wise_Resolution_Comparison()

    return render_template("resolution-insights.html",graph9=graph9,graph91=graph91)

@app.route('/trend-analysis')
def trend_analysis():
    graph10 = Monthly_Query_Trend()
    graph11 = Yearly_Trend_Breakdown()

    return render_template("trend-analysis.html",graph10=graph10,graph11=graph11)



if __name__ == '__main__':
    app.run(debug=True)
