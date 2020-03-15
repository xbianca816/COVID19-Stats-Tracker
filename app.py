# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import math 
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from opencage.geocoder import OpenCageGeocode
from pprint import pprint
from openpyxl import load_workbook
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
# from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dt
import plotly
import flask
import copy



# read in data
path = '/Users/xb/Desktop/Corona'
path_data = os.listdir(path)
path_data = [x for x in path_data if 'data.xls' in x]
print(path_data)
# loop through all data files and combine into master df
# loop through all tabs in each file and save into one master df
xl_file = pd.ExcelFile('./data.xls')
print(xl_file)

df_master = pd.DataFrame()

for x in path_data:
    # loop through all data files
    path_temp = os.path.join(path, x)
    df_temp = pd.read_excel(path_temp, sheet_name=None)
    
    # loop through all tabs in each data file
    df_full_table = pd.DataFrame()
    for sheetname, sheet in df_temp.items():
        sheet['SheetName'] = sheetname
        df_full_table = df_full_table.append(sheet)
    df_full_table.reset_index(inplace=True, drop=True)
    
    # combine into master dataframe
    df_master = pd.concat([df_master, df_full_table])



# clean data
# replace mainland china with china
df_master['Country/Region'].replace(to_replace = 'Mainland China', value = 'China', inplace=True)
# replace NaN with 0
df_master.replace(to_replace=np.nan, value=0)    
# df_master = df_master.fillna(0)

# change dtypes to integer
for col in ['Confirmed', 'Deaths', 'Recovered', 'Suspected']:
    df_master[col] = df_master[col].fillna(0)
    df_master[col] = df_master[col].astype(int)


latest_date = df_master['SheetName'].max()
latest_date_timestamp = df_master['Last Update'].max()


df_master.to_csv(latest_date+"_data.csv", encoding = 'utf-8')

# for data table
df_master_sum = df_master.loc[df_master['SheetName']==latest_date].groupby(by=['Country/Region', 'Last Update'], sort=False).sum().sort_values(by=['Confirmed'], ascending=False).reset_index()


daysOutbreak = (datetime.strptime(df_master['SheetName'][0],'%Y-%m-%d-%H-%M') - datetime.strptime('12/31/2019', '%m/%d/%Y')).days


# Save numbers into variables to use in the app
confirmedCases = df_master.loc[df_master['SheetName']==latest_date]['Confirmed'].sum()
deathsCases = df_master.loc[df_master['SheetName']==latest_date]['Deaths'].sum()
recoveredCases = df_master.loc[df_master['SheetName']==latest_date]['Recovered'].sum()


df_master['Last Update'] = '0' + df_master['Last Update'] 
df_master['Date_last_updated'] = [datetime.strptime(d, '%Y-%m-%d-%H-%M') for d in df_master['SheetName']]
df_master['Date_str'] = [datetime.strftime(d, '%Y-%m-%d') for d in df_master['Date_last_updated']]




def df_for_lineplot_diff(df, CaseType):
    '''This is the function for construct df for line plot'''
    
    assert type(CaseType) is str, "CaseType must be one of the following three strings Confirmed/Recovered/Deaths"
    
    
    # Construct confirmed cases dataframe for line plot
    DateList = []
    ChinaList =[]
    OtherList = []
    
    dfTpm = pd.DataFrame(df_master.groupby(['Country/Region', 'Date_last_updated'])[CaseType].agg(np.sum)).reset_index()

    # len 18, from oldest to latest
    DateList.append(dfTpm['Date_last_updated'].sort_values().unique())
    DateList = dfTpm['Date_last_updated'].sort_values().unique()
    ChinaList = dfTpm.loc[dfTpm['Country/Region'] == 'China'].groupby(dfTpm['Date_last_updated'], as_index=False).sum()[CaseType].tolist()
    OtherList = dfTpm.loc[dfTpm['Country/Region'] != 'China'].groupby(dfTpm['Date_last_updated'], as_index=False).sum()[CaseType].tolist()

    # cum sum
#     ChinaList = list(cumsum(ChinaList))
#     OtherList = list(cumsum(OtherList))

    df = pd.DataFrame({'Date':DateList,
                       'Mainland China':ChinaList,
                       'Other locations':OtherList})
    df['Total']=df['Mainland China']+df['Other locations']
    
    
    
    # working on it - optional
    # Calculate differenec in a 24-hour window
    df_reversed = df.iloc[::-1].reset_index()

    # define a largest <= 24 hour window between the latest and the second latest timestamp

    for index, _ in df_reversed.iterrows():
        diff = df_reversed['Date'].max() - df_reversed['Date'][index]
#         print(df_reversed['Date'].max(), df_reversed['Date'][index], diff)
        if diff.days==1:
            break

#     print(df_reversed['Total'][0], df_reversed['Total'][index])
    plusNum = df_reversed['Total'][0] -  df_reversed['Total'][index]
    plusPercentNum = float((df_reversed['Total'][0] - df_reversed['Total'][index])/float(df_reversed['Total'][index]))
    print(type(plusPercentNum))
#     plusPercentNum = "{:.2%}".format(plusPercentNum)
#     # Select the latest data from a given date
#     df['date_day']=[d.date() for d in df['Date']]
#     df=df.groupby(by=df['date_day'], sort=False).transform(max).drop_duplicates(['Date'])
    
#     df=df.reset_index(drop=True)
    
    return df, plusNum, plusPercentNum


dfs = df_master
# Construct confirmed cases dataframe for line plot and 24-hour window case difference
df_confirmed, plusConfirmedNum, plusPercentNum1 = df_for_lineplot_diff(dfs, 'Confirmed')


# Construct recovered cases dataframe for line plot and 24-hour window case difference
df_recovered, plusRecoveredNum, plusPercentNum2 = df_for_lineplot_diff(dfs, 'Recovered')


# Construct death case dataframe for line plot and 24-hour window case difference
df_deaths, plusDeathNum, plusPercentNum3 = df_for_lineplot_diff(dfs, 'Deaths')




#############################################################################################
#### Start to make plots
#############################################################################################
# Line plot for confirmed cases
# Set up tick scale based on confirmed case number - NEED TO BE AUTOMATED LATER, HARDCODED FOR NOW
tickList = list(np.arange(0, df_confirmed['Mainland China'].max()+1000, 10000))

# hard code y axis ticks for now
# tickList = [0, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 10000]


# Create empty figure canvas
fig_confirmed = go.Figure()
# Add trace to the figure
fig_confirmed.add_trace(go.Scatter(x=df_confirmed['Date'], y=df_confirmed['Mainland China'],
                                   mode='lines+markers',
                                   line_shape='spline',
                                   name='Mainland China',
                                   line=dict(color='#921113', width=4),
                                   marker=dict(size=4, color='#f4f4f2',
                                               line=dict(width=1,color='#921113')),
                                   text=[datetime.strftime(d, '%b %d %Y') for d in df_confirmed['Date']],
                                   hovertext=['Mainland China confirmed<br>{:,d} cases<br>'.format(i) for i in df_confirmed['Mainland China']],
                                   hovertemplate='<b>%{text}</b><br></br>'+
                                                 '%{hovertext}'+
                                                 '<extra></extra>'))
fig_confirmed.add_trace(go.Scatter(x=df_confirmed['Date'], y=df_confirmed['Other locations'],
                                   mode='lines+markers',
                                   line_shape='spline',
                                   name='Other Region',
                                   line=dict(color='#eb5254', width=4),
                                   marker=dict(size=4, color='#f4f4f2',
                                               line=dict(width=1,color='#eb5254')),
                                   text=[datetime.strftime(d, '%b %d %Y') for d in df_confirmed['Date']],
                                   hovertext=['Other region confirmed<br>{:,d} cases<br>'.format(i) for i in df_confirmed['Other locations']],
                                   hovertemplate='<b>%{text}</b><br></br>'+
                                                 '%{hovertext}'+
                                                 '<extra></extra>'))
# Customise layout
fig_confirmed.update_layout(
#    title=dict(
#    text="<b>Confirmed Cases Timeline<b>",
#    y=0.96, x=0.5, xanchor='center', yanchor='top',
#    font=dict(size=20, color="#292929", family="Playfair Display")
#   ),
    margin=go.layout.Margin(
        l=10,
        r=10,
        b=10,
        t=5,
        pad=0
    ),
    yaxis=dict(
        showline=False, linecolor='#272e3e',
        zeroline=False,
        #showgrid=False,
        gridcolor='rgba(203, 210, 211,.3)',
        gridwidth = .1,
        tickmode='array',
        # Set tick range based on the maximum number
        tickvals=tickList,
        # Set tick label accordingly
        ticktext=["{:.0f}k".format(i/1000) for i in tickList],
  

    ),
#    yaxis_title="Total Confirmed Case Number",
    xaxis=dict(
        showline=False, linecolor='#272e3e',
        showgrid=False,
        gridcolor='rgba(203, 210, 211,.3)',
        gridwidth = .1,
        zeroline=False
    ),
    xaxis_tickformat='%b %d',
    hovermode = 'x',
    legend_orientation="h",
#    legend=dict(x=.35, y=-.05),
    plot_bgcolor='#ffffff',
    paper_bgcolor='#ffffff',
    font=dict(color='#292929')
)





# Line plot for combine cases
# Set up tick scale based on confirmed case number
tickList = list(np.arange(0, df_recovered['Mainland China'].max()+1000, 5000))

# Create empty figure canvas
fig_combine = go.Figure()
# Add trace to the figure
fig_combine.add_trace(go.Scatter(x=df_recovered['Date'], y=df_recovered['Total'],
                                   mode='lines+markers',
                                   line_shape='spline',
                                   name='Total Recovered Cases',
                                   line=dict(color='#168038', width=4),
                                   marker=dict(size=4, color='#f4f4f2',
                                               line=dict(width=1,color='#168038')),
                                   text=[datetime.strftime(d, '%b %d %Y AEDT') for d in df_recovered['Date']],
                                   hovertext=['Total recovered<br>{:,d} cases<br>'.format(i) for i in df_recovered['Total']],
                                   hovertemplate='<b>%{text}</b><br></br>'+
                                                 '%{hovertext}'+
                                                 '<extra></extra>'))
fig_combine.add_trace(go.Scatter(x=df_deaths['Date'], y=df_deaths['Total'],
                                mode='lines+markers',
                                line_shape='spline',
                                name='Total Death Cases',
                                line=dict(color='#626262', width=4),
                                marker=dict(size=4, color='#f4f4f2',
                                            line=dict(width=1,color='#626262')),
                                text=[datetime.strftime(d, '%b %d %Y AEDT') for d in df_deaths['Date']],
                                hovertext=['Total death<br>{:,d} cases<br>'.format(i) for i in df_deaths['Total']],
                                hovertemplate='<b>%{text}</b><br></br>'+
                                              '%{hovertext}'+
                                              '<extra></extra>'))
# Customise layout
fig_combine.update_layout(
#    title=dict(
#    text="<b>Confirmed Cases Timeline<b>",
#    y=0.96, x=0.5, xanchor='center', yanchor='top',
#    font=dict(size=20, color="#292929", family="Playfair Display")
#   ),
    margin=go.layout.Margin(
        l=10,
        r=10,
        b=10,
        t=5,
        pad=0
    ),
    yaxis=dict(
        showline=False, linecolor='#272e3e',
        zeroline=False,
        #showgrid=False,
        gridcolor='rgba(203, 210, 211,.3)',
        gridwidth = .1,
        tickmode='array',
        # Set tick range based on the maximum number
        tickvals=tickList,
        # Set tick label accordingly
        ticktext=["{:.0f}k".format(i/1000) for i in tickList]
    ),
#    yaxis_title="Total Confirmed Case Number",
    xaxis=dict(
        showline=False, linecolor='#272e3e',
        showgrid=False,
        gridcolor='rgba(203, 210, 211,.3)',
        gridwidth = .1,
        zeroline=False
    ),
    xaxis_tickformat='%b %d',
    hovermode = 'x',
    legend_orientation="h",
#    legend=dict(x=.35, y=-.05),
    plot_bgcolor='#ffffff',
    paper_bgcolor='#ffffff',
    font=dict(color='#292929')
)



# Line plot for death rate cases
# Set up tick scale based on confirmed case number
tickList = list(np.arange(0, (df_deaths['Mainland China']/df_confirmed['Mainland China']*100).max(), 0.5))

# Create empty figure canvas
fig_rate = go.Figure()
# Add trace to the figure
fig_rate.add_trace(go.Scatter(x=df_deaths['Date'], y=df_deaths['Mainland China']/df_confirmed['Mainland China']*100,
                                mode='lines+markers',
                                line_shape='spline',
                                name='Mainland China',
                                line=dict(color='#626262', width=4),
                                marker=dict(size=4, color='#f4f4f2',
                                            line=dict(width=1,color='#626262')),
                                text=[datetime.strftime(d, '%b %d %Y AEDT') for d in df_deaths['Date']],
                                hovertext=['Mainland China death rate<br>{:.2f}%'.format(i) for i in df_deaths['Mainland China']/df_confirmed['Mainland China']*100],
                                hovertemplate='<b>%{text}</b><br></br>'+
                                              '%{hovertext}'+
                                              '<extra></extra>'))
fig_rate.add_trace(go.Scatter(x=df_deaths['Date'], y=df_deaths['Other locations']/df_confirmed['Other locations']*100,
                                mode='lines+markers',
                                line_shape='spline',
                                name='Other Region',
                                line=dict(color='#a7a7a7', width=4),
                                marker=dict(size=4, color='#f4f4f2',
                                            line=dict(width=1,color='#a7a7a7')),
                                text=[datetime.strftime(d, '%b %d %Y AEDT') for d in df_deaths['Date']],
                                hovertext=['Other region death rate<br>{:.2f}%'.format(i) for i in df_deaths['Other locations']/df_confirmed['Other locations']*100],
                                hovertemplate='<b>%{text}</b><br></br>'+
                                              '%{hovertext}'+
                                              '<extra></extra>'))

# Customise layout
fig_rate.update_layout(
    margin=go.layout.Margin(
        l=10,
        r=10,
        b=10,
        t=5,
        pad=0
    ),
    yaxis=dict(
        showline=False, linecolor='#272e3e',
        zeroline=False,
        #showgrid=False,
        gridcolor='rgba(203, 210, 211,.3)',
        gridwidth = .1,
        tickmode='array',
        # Set tick range based on the maximum number
        tickvals=tickList,
        # Set tick label accordingly
        ticktext=['{:.1f}'.format(i) for i in tickList]
    ),
#    yaxis_title="Total Confirmed Case Number",
    xaxis=dict(
        showline=False, linecolor='#272e3e',
        showgrid=False,
        gridcolor='rgba(203, 210, 211,.3)',
        gridwidth = .1,
        zeroline=False
    ),
    xaxis_tickformat='%b %d',
    hovermode = 'x',
    legend_orientation="h",
#    legend=dict(x=.35, y=-.05),
    plot_bgcolor='#ffffff',
    paper_bgcolor='#ffffff',
    font=dict(color='#292929')
)


# keep for table
columnList = ['Country/Region', 'Confirmed', 'Deaths', 'Recovered', 'Remaining']
columns = [{'name': i, 'id': i} for i in df_master_sum.loc[:, df_master_sum.columns.isin(columnList)]]

# create sum dfs for interactive table

df_master_sum = df_master_sum.replace({'Country/Region':'China'}, 'Mainland China')
df_master_sum['Remaining'] = df_master_sum['Confirmed'] - df_master_sum['Recovered'] - df_master_sum['Deaths']
# Rearrange columns to correspond to the number plate order
df_master_sum = df_master_sum[['Country/Region','Remaining','Confirmed','Recovered','Deaths','Latitude','Longitude']]
# Sort value based on Remaining cases and then Confirmed cases
df_master_sum = df_master_sum.sort_values(by=['Remaining', 'Confirmed'], ascending=False).reset_index(drop=True)
# Set row ids pass to selected_row_ids
df_master_sum['id'] = df_master_sum['Country/Region']
df_master_sum.set_index('id', inplace=True, drop=False)



#############################################################################################
#### Dash App
#############################################################################################

app = dash.Dash(__name__)
server = app.server


# declare global layout
# Boostrap CSS.
app.css.append_css({'external_url': 'https://cdn.rawgit.com/plotly/dash-app-stylesheets/2d266c578d2a6e8850ebce48fdb52759b2aef506/stylesheet-oil-and-gas.css'})  # noqa: E501

# API keys and datasets
privitate_mapbox_access_token = 'sk.eyJ1IjoieGJpYW5jYTgxNiIsImEiOiJjazc3djZqaGEwYzBpM2V0ZnlmNTh6Y2x2In0.Ocn_hLKpQVb3NRS1ci4ykQ'
map_data = df_master

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
# from app import app
# from panels import opportunities, cases, leads


server = app.server

app.layout = html.Div(
    [
        html.Div(
            className="row header",
            children=[
                html.Button(id="menu", children=dcc.Markdown("&#8801")),
                html.Span(
                    className="app-title",
                    children=[
                        dcc.Markdown("**Coronavirus (COVID-19) Outbreak Statistics Tracker**"),
                        html.Span(
                            id="subtitle",
                            children=dcc.Markdown("&nbsp"),
                            style={"font-size": "1.2rem", "margin-top": "15px"},
                        ),
                    ],
                ),
#                 html.P(
#                     id="description",
#                     children='This dashboard is designed to track COVID-19 confirmed/recovered/death cases around the world. It continually queries databases and updates cases for all countries on a daily basis.'
#                 ),
#                 html.Img(src=app.get_asset_url("logo.png")),
                html.A(
                    id="learn_more",
                    children=html.Button("Learn More"),
                    href="https://www.arcgis.com/apps/opsdashboard/index.html#/bda7594740fd40299423467b48e9ecf6",
                ),
         
            ],
        ),
        
      html.Div(
        className="row header",
        children=[                          
            html.P(
                className="indicator",
                children="This dashboard is developed to track and visualize the latest status of and growth rate of reported \
                confirmed/recovered/death cases acround the world on a daily basis.", 
            ),
        ]
      ), 
        
        # row headers
        html.Div(
            id="tabs",
            className="row tabs",
#             children=[
#                 dcc.Link("Confirmed", href="/"),
#                 dcc.Link("Death", href="/"),
#                 dcc.Link("Recovered", href="/"),
#             ],
        ),
        
        
#         html.Div(
#             id="opportunity_indicators",
#             className="row indicators",
#             children=[
#                 indicator(
#                     "#00cc96", "Won opportunities", "left_opportunities_indicator"
#                 ),
#                 indicator(
#                     "#119DFF",
#                     "Open opportunities",
#                     "middle_opportunities_indicator",
#                 ),
#                 indicator(
#                     "#EF553B", "Lost opportunities", "right_opportunities_indicator"
#                 ),
#             ],
#         ),
        
        
        html.Div(
            id="number-plate",
            style={'marginLeft':'1.5%','marginRight':'1.5%','marginBottom':'.5%'},
                 children=[
                     html.Div(
                         style={'width':'24.4%','backgroundColor':'#ffffff','display':'inline-block',
                                'marginRight':'.8%','verticalAlign':'top'},
                              children=[
                                  html.H3(style={'textAlign':'center',
                                                 'fontWeight':'bold','color':'#000000'},
                                               children=[
                                                   html.P(style={'color':'#ffffff','padding':'.5rem'},
                                                              children='xxxx xx xxx xxxx xxx xxxxx')
#                                                    ,'{}'.format(daysOutbreak),
                                               ]),
                                  html.H5(style={'textAlign':'center','color':'#000000','padding':'.1rem', 'font-size':'1.5rem'},
                                               children='{}'.format(daysOutbreak)),   
                                  html.H5(style={'textAlign':'center','color':'#000000','padding':'.1rem', 'font-size':'.8rem'},
                                               children="Days Since Outbreak")                                        
                                       ])
                      ,
                     
                     html.Div(
                         style={'width':'24.4%','backgroundColor':'#ffffff','display':'inline-block',
                                'marginRight':'.8%','verticalAlign':'top'},
                              children=[
                                  html.H3(style={'textAlign':'center',
                                                 'fontWeight':'bold','color':'#000000'},
                                                children=[
                                                    html.P(style={'padding':'.5rem'},
                                                              children='+ {:,d} in the past 24h ({:.1%})'.format(plusConfirmedNum, plusPercentNum1))
#                                                     ,'{:,d}'.format(confirmedCases)
                                                         ]),
                                  html.H5(style={'textAlign':'center','color':'#000000', 'font-size':'1.5rem'},
                                               children='{:,d}'.format(confirmedCases)), 
                                  html.H5(style={'textAlign':'center','color':'#000000','padding':'.1rem', 'font-size':'.8rem'},
                                               children="Confirmed Cases")                                        
                                       ])
                     ,
                     html.Div(
                         style={'width':'24.4%','backgroundColor':'#ffffff','display':'inline-block',
                                'marginRight':'.8%','verticalAlign':'top'},
                              children=[
                                  html.H3(style={'textAlign':'center',
                                                       'fontWeight':'bold','color':'#000000'},
                                               children=[
                                                   html.P(style={'padding':'.5rem'},
                                                              children='+ {:,d} in the past 24h ({:.1%})'.format(plusRecoveredNum, plusPercentNum2))
#                                                    ,'{:,d}'.format(recoveredCases),
                                               ]),
                                    html.H5(style={'textAlign':'center','color':'#000000', 'font-size':'1.5rem'},
                                   children='{:,d}'.format(recoveredCases)), 
                                  html.H5(style={'textAlign':'center','color':'#000000','padding':'.1rem', 'font-size':'.8rem'},
                                               children="Recovered Cases")                                        
                                       ])
                     ,
                     html.Div(
                         style={'width':'24.4%','backgroundColor':'#ffffff','display':'inline-block',
                                'verticalAlign':'top'},
                              children=[
                                  html.H3(style={'textAlign':'center',
                                                       'fontWeight':'bold','color':'#000000'},
                                                children=[
                                                    html.P(style={'padding':'.5rem'},
                                                              children='+ {:,d} in the past 24h ({:.1%})'.format(plusDeathNum, plusPercentNum3))
#                                                     ,'{:,d}'.format(deathsCases)
                                                ]),
                                  html.H5(style={'textAlign':'center','color':'#000000', 'font-size':'1.5rem'},
                                               children='{:,d}'.format(deathsCases)), 
                                  html.H5(style={'textAlign':'center','color':'#000000','padding':'.1rem', 'font-size':'.8rem'},
                                               children="Death Cases")                                        
                                       ])
                          ]),
        
        # map 
         html.Div(
            id='dcc-map',
            style={'marginLeft':'1.5%','marginRight':'1.5%','marginBottom':'.5%'},
                 children=[
                     html.Div(style={'width':'66.41%','marginRight':'.8%','display':'inline-block','verticalAlign':'top'},
                              children=[
                                  html.H5(style={'textAlign':'center','backgroundColor':'#ffffff',
                                                 'color':'#000000','padding':'1rem','marginBottom':'0'},
                                               children='Latest Coronavirus Outbreak Map'),
                                  dcc.Graph(
                                      id='datatable-interact-map',
                                      style={'height':'500px'},
                                  )
                              ]
                             ),
                     html.Div(style={'width':'32.79%','display':'inline-block','verticalAlign':'top'},
                              children=[
                                  html.H5(style={'textAlign':'center','backgroundColor':'#ffffff',
                                                 'color':'#000000','padding':'1rem','marginBottom':'0'},
                                               children='Cases by Country/Region'),
                                  dash_table.DataTable(
                                      id='datatable-interact-location',
                                      # Don't show coordinates
                                      columns = [{'name': i, 'id': i} for i in df_master_sum.loc[:, df_master_sum.columns.isin(columnList)]],
#                                       columns=[{"name": i, "id": i} for i in df_master.columns[0:5]],
                                      # But still store coordinates in the table for interactivity
                                      data=df_master_sum.to_dict("rows"),
                                      row_selectable="single",
                                      #selected_rows=[],
                                      sort_action="native",
                                      style_as_list_view=True,
                                      style_cell={
                                          'font_family':'Arial',
                                          'padding':'.1rem',
                                          'font_size': '0.7rem',
                                          'backgroundColor':'#ffffff',
                                      },
#                                       fixed_rows={'headers':True,'data':0},
                                      style_table={
                                          'minHeight': '500px', 
                                          'height': '500px', 
                                          'maxHeight': '500px',
                                          'overflowY':'scroll',
                                          'overflowX':'scroll',
                                      },
        
                                      style_header={
                                        'backgroundColor':'#ffffff',
                                        'fontWeight':'bold',
                                        'padding': '0.1rem'
                                        
                                      },
                                      style_cell_conditional=[
                                          {'if': {'column_id':'Country/Regions'},'width':'28%'},
                                          {'if': {'column_id':'Remaining'},'width':'18%'},
                                          {'if': {'column_id':'Confirmed'},'width':'18%'},
                                          {'if': {'column_id':'Recovered'},'width':'18%'},
                                          {'if': {'column_id':'Deaths'},'width':'18%'},
                                          {'if': {'column_id':'Confirmed'},'color':'#d7191c'},
                                          {'if': {'column_id':'Recovered'},'color':'#1a9622'},
                                          {'if': {'column_id':'Deaths'},'color':'#6c6c6c'},
                                          {'textAlign': 'center'}
                                      ],
                                  )
                              ])
                 ]
         ),
        
         html.Div(
            id='dcc-plot',
            style={'marginLeft':'1.5%','marginRight':'1.5%','marginBottom':'.35%','marginTop':'.5%'},
                 children=[
                     html.Div(
                         style={'width':'32.79%','display':'inline-block','marginRight':'.8%','verticalAlign':'top'},
                              children=[
                                  html.H5(style={'textAlign':'center','backgroundColor':'#ffffff',
                                                 'color':'#000000','padding':'1rem','marginBottom':'0'},
                                               children='Confirmed Case Timeline'),
                                  dcc.Graph(style={'height':'300px'},figure=fig_confirmed)])
                     ,
                     html.Div(
                         style={'width':'32.79%','display':'inline-block','marginRight':'.8%','verticalAlign':'top'},
                              children=[
                                  html.H5(style={'textAlign':'center','backgroundColor':'#ffffff',
                                                 'color':'#000000','padding':'1rem','marginBottom':'0'},
                                               children='Recovered/Death Case Timeline'),
                                  dcc.Graph(style={'height':'300px'},figure=fig_combine)]),
                     html.Div(
                         style={'width':'32.79%','display':'inline-block','verticalAlign':'top'},
                              children=[
                                  html.H5(style={'textAlign':'center','backgroundColor':'#ffffff',
                                                 'color':'#000000','padding':'1rem','marginBottom':'0'},
                                               children='Death Rate (%) Timeline'),
                                  dcc.Graph(style={'height':'300px'},figure=fig_rate)])])
      
        

    ]
)
#     ])



@app.callback(
    Output('datatable-interact-map', 'figure'),
    [Input('datatable-interact-location', 'derived_virtual_selected_rows'),
     Input('datatable-interact-location', 'selected_row_ids')]
)

def update_figures(row_ids, selected_row_ids):
    # When the table is first rendered, `derived_virtual_data` and
    # `derived_virtual_selected_rows` will be `None`. This is due to an
    # idiosyncracy in Dash (unsupplied properties are always None and Dash
    # calls the dependent callbacks when the component is first rendered).
    # So, if `rows` is `None`, then the component was just rendered
    # and its value will be the same as the component's dataframe.
    # Instead of setting `None` in here, you could also set
    # `derived_virtual_data=df.to_rows('dict')` when you initialize
    # the component.
        
    if row_ids is None:
        row_ids = []
        
    dff = df_master
        
    mapbox_access_token = 'pk.eyJ1IjoieGJpYW5jYTgxNiIsImEiOiJjazc3djRham8wYW1iM2dvMnNvdnBoemdxIn0.AEbyhcI85Xx8ngPxEFBI_w'    
#     mapbox_access_token = 'sk.eyJ1IjoieGJpYW5jYTgxNiIsImEiOiJjazc3djZqaGEwYzBpM2V0ZnlmNTh6Y2x2In0.Ocn_hLKpQVb3NRS1ci4ykQ'

    
     # Generate a list for hover text display
    textList = []
    for area, region in zip(df_master['Province/State'], df_master['Country/Region']):
        if type(area) is str:
                if region == "Hong Kong" or region == "Macau" or region == "Taiwan":
                    textList.append(area)
#                 elif region == 'United States' or region == 'US'""
                else:
                    textList.append(area+', '+region)
        else:
            textList.append(region)

    # Generate a list for color gradient display
    colorList=[]
    for comfirmed, recovered, deaths in zip(df_master['Confirmed'],df_master['Recovered'],df_master['Deaths']):
    #     print(comfirmed, recovered, deaths)
        try:
            remaining = recovered / (comfirmed - deaths)
            colorList.append(remaining)
        except ZeroDivisionError:
            remaining = 0
            
    

    fig = go.Figure(go.Scattermapbox(
    lat=df_master['Lat'],
    lon=df_master['Lng'],
    mode='markers',
    marker=go.scattermapbox.Marker(
        color=['#d7191c' if i < 1 else '#1a9622' for i in colorList],
        size=[i**(1/3) for i in df_master['Confirmed']], 
        sizemin=1,
        sizemode='area',
        sizeref=2.*max([math.sqrt(i) for i in df_master['Confirmed']])/(100.**2),
    ),
    text=textList,
    hovertext=['Comfirmed: {}<br>Recovered: {}<br>Death: {}'.format(i, j, k) for i, j, k in zip(df_master['Confirmed'],
                                                                                                df_master['Recovered'],
                                                                                                df_master['Deaths'])],
    hovertemplate = "<b>%{text}</b><br><br>" +
                    "%{hovertext}<br>" +
                    "<extra></extra>")
    )

    # map annotation    
    map_annotation =[
        dict(
            x=.5,
            y=-.01,
            align='center',
            showarrow=False,
            text="Points are placed based on data geolocation levels.<br><b>Province/State level<b> - China, Australia, United States, and Canada; <b>Country level<b> - other countries.",
            xref="paper",
            yref="paper",
            font=dict(size=10, color='#FFFFFF'),
        )]
    
    # map layout
    layout =  dict(
        margin = dict(t = 0, b = 0, l = 0, r = 0),
        font = dict(color = '#FFFFFF', size = 11),
        paper_bgcolor = '#000000',
        hovermode = 'closest',
        transition = {'duration': 50},
        annotations = map_annotation,
        mapbox = dict(
            accesstoken = mapbox_access_token,
            bearing = 0,
            center = dict(
#                 30.583332, 114.283333 - coordinate of Wuhan
                lat=30.583332 if len(row_ids)==0 else dff.loc[selected_row_ids[0]].lat, 
                lon=114.283333 if len(row_ids)==0 else dff.loc[selected_row_ids[0]].lon
        ),
        # we want the map to be "parallel" to our screen, with no angle
        pitch = 0,
        # default level of zoom
        zoom = 3,
        # default map style
        style = 'dark'
    )
    )
    
    fig.update_layout(layout)

    
    
    # more layout updates
    updatemenus=[
    # drop-down 1: map styles menu
    # buttons containes as many dictionaries as many alternative map styles I want to offer
    dict(
        buttons=list([
            dict(
                args=['mapbox.style', 'dark'],
                label='Dark',
                method='relayout'
            ),                    
            dict(
                args=['mapbox.style', 'light'],
                label='Light',
                method='relayout'
            ),
            dict(
                args=['mapbox.style', 'outdoors'],
                label='Outdoors',
                method='relayout'
            ),
            dict(
                args=['mapbox.style', 'satellite-streets'],
                label='Satellite with Streets',
                method='relayout'
            )                    
        ]),
        # direction where I want the menu to expand when I click on it
        direction = 'up',
      
        # here I specify where I want to place this drop-down on the map
        x = 0.75,
        xanchor = 'left',
        y = 0.05,
        yanchor = 'bottom',
      
        # specify font size and colors
        bgcolor = '#000000',
        bordercolor = '#FFFFFF',
        font = dict(size=11)
    )]
    
    fig.update_layout(updatemenus= updatemenus)



    return fig
    
    
    
    
    
    




if __name__ == '__main__':
    app.run_server(debug=False)







