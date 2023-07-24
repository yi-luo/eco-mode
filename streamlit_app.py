from collections import namedtuple
import altair as alt
import math
import pandas as pd
import streamlit as st
import requests
import json

### local run command: streamlit run eco-mode.py 
## resources:
## https://ourworldindata.org/travel-carbon-footprint

## app configuation
st.set_page_config(
    page_title='EcoMode', 
    page_icon='🍃', 
    layout='centered',
    )
st.subheader("""Navigate greener ways to travel.""")

distance_unit_selection = st.sidebar.radio(
    "Unit of Distance",
    ("Kilometres", "Miles")
)
api_distance_unit = "metric"
if distance_unit_selection == "Miles":
    api_distance_unit = "imperial"

car_type_selection = st.sidebar.radio(
    "Car Type",
    ("Gas", "Diesel", "Electric", "Hybrid")
)


## user input
location_start = st.text_input(
    label='Where from?', 
    placeholder='e.g. Vancouver',
    )

location_end = st.text_input(
    label='Where to?', 
    placeholder='e.g. Seattle'
    )

## constants
miles_km_ratio = 1.60934
co2_grams_km_mapping = {
    "Gas": 192, 
    "Diesel": 171, 
    "Electric": 53, 
    "Hybrid": 109,
    "ShortFlight": 255,
    "MediumFlight": 156,
    "LongFlight": 150,
    "Bus": 105,
    "Train": 41, ##6g for Eurostar (renewables), 41g for other
    "Bike": 0,
    "Walk": 0,
    }

@st.cache_data
def apiCall(origin, destination, distance_unit, mode, transit_mode):
    api_key = st.secrets["API_KEY"]
    car_url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={destination}&units={distance_unit}&key={api_key}&mode={mode}&transit_mode={transit_mode}"
    return json.loads(requests.request("GET", car_url, headers={}, data={}).text)

def getStatus(response):
    return response["rows"][0]["elements"][0]["status"]

def getRouteDetails(status, response, mode):
    ## return distance, time, co2emissions
    if status == "ZERO_RESULTS" or status == "MAX_ROUTE_LENGTH_EXCEEDED":
        time = "N/A"
        co2_kilograms = "N/A"
    elif status == "OK":
        time = response["rows"][0]["elements"][0]["duration"]["text"]
        distance_km = response["rows"][0]["elements"][0]["distance"]["value"] / 1000
        round_co2_kilograms = round((distance_km * co2_grams_km_mapping[mode]) / 1000)
        co2_kilograms = str(round_co2_kilograms) + " kg"
    return time, co2_kilograms

## call api and calculate co2 emissions
if location_start and location_end:
    # car driving details
    car_response = apiCall(location_start, location_end, api_distance_unit, mode="driving", transit_mode="")
    car_status = getStatus(car_response)

    if car_status == "NOT_FOUND":
        st.warning("One of the inputs cannot be geocoded")
        st.stop()
    elif car_status == "ZERO_RESULTS" or car_status == "MAX_ROUTE_LENGTH_EXCEEDED":
        st.warning("No driving route found")
        st.stop()

    start_address = car_response["origin_addresses"][0]
    end_address = car_response["destination_addresses"][0]

    # car
    car_distance_text = car_response["rows"][0]["elements"][0]["distance"]["text"]
    car_distance_km = car_response["rows"][0]["elements"][0]["distance"]["value"] / 1000
    car_time, selected_car_co2_kilograms = getRouteDetails(car_status, car_response, mode=car_type_selection)

    car_gas_co2_kilograms = (car_distance_km * co2_grams_km_mapping["Gas"]) / 1000
    car_diesel_co2_kilograms = (car_distance_km * co2_grams_km_mapping["Diesel"]) / 1000
    car_electric_co2_kilograms = (car_distance_km * co2_grams_km_mapping["Electric"]) / 1000
    car_hybrid_co2_kilograms = (car_distance_km * co2_grams_km_mapping["Hybrid"]) / 1000

    # transit: bus
    transit_bus_response = apiCall(location_start, location_end, api_distance_unit, mode="transit", transit_mode="bus")
    transit_bus_status = getStatus(transit_bus_response)
    transit_bus_time, transit_bus_co2_kilograms = getRouteDetails(transit_bus_status, transit_bus_response, mode="Bus")
    
    # # transit: train
    transit_train_response = apiCall(location_start, location_end, api_distance_unit, mode="transit", transit_mode="train")
    transit_train_status = getStatus(transit_train_response)
    transit_train_time, transit_train_co2_kilograms = getRouteDetails(transit_train_status, transit_train_response, mode="Train")


    # display
    st.markdown("Going from **" + start_address+"** to **"+end_address+'**')
    st.metric(label='Distance', value=car_distance_text)
    tab1, tab2 = st.tabs(["Transportation Modes", "Car Types"])
    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label="Car: "+ str(car_type_selection), 
                value=selected_car_co2_kilograms, 
                delta=car_time,
                delta_color="off",
                )
        with col2:
            st.metric(
                label="Bus", 
                value=transit_bus_co2_kilograms, 
                delta=transit_bus_time,
                delta_color="off",
                )
        with col3:
            st.metric(
                label="Train", 
                value=transit_train_co2_kilograms, 
                delta=transit_train_time,
                delta_color="off",
                help="Diesel powered trains"
                )
            
    with tab2:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label='Gas', value=str(round(car_gas_co2_kilograms))+" kg")
        with col2:
            st.metric(label='Diesel', value=str(round(car_diesel_co2_kilograms))+" kg")
        with col3:
            st.metric(label='Electric', value=str(round(car_electric_co2_kilograms))+" kg")
        with col4:
            st.metric(label='Hybrid', value=str(round(car_hybrid_co2_kilograms))+" kg")


## metrics: distance/time, cost/time, 

