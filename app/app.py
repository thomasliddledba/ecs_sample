'''
PecNet
'''
import streamlit as st
import requests
import boto3 as aws
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Patch all supported libraries for X-Ray
patch_all()

# Initialize X-Ray recorder and add Streamlit middleware
xray_recorder.configure(service='PecNet')
def get_api_key():
    '''
    Retrieves the SSM Paramenter Store value for the API Key
    '''
    xray_recorder.begin_subsegment('get_api_key_ssm')
    ssm = aws.client("ssm")
    parameter = ssm.get_parameter(Name="PecNetAppApiKey", WithDecryption=True)
    xray_recorder.end_subsegment()
    return parameter["Parameter"]["Value"]

# Function to get weather data
def get_weather(data):
    '''
    Gets the current weather basted on the city value being passed
    '''
    xray_recorder.begin_subsegment('get_weather_data')
    xray_recorder.put_metadata("user_query", data)
    api_key = get_api_key()
    if api_key == 'N/A':
        st.error("404 - The API Key is incorrect or not defined in the Parameter Store.")

    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": data, "appid": api_key, "units": "metric"}
    response = requests.get(base_url, params=params, timeout=5)
    xray_recorder.end_subsegment()
    return response.json()


# Streamlit GUI
st.set_page_config(page_title='PecNet App', page_icon=':thermometer:')
st.title("PecNet App")
city_zip_code = st.text_input("Enter a city:")
if st.button("Get Weather"):
    xray_recorder.begin_segment('PecNet')
    weather_data = get_weather(city_zip_code)
    if weather_data.get("cod") != 200:
        st.error(weather_data.get("cod"))
    else:
        st.write(f"City:  {weather_data['name']}")
        st.write(f"Temperature: {round((weather_data['main']['temp'] * 1.8) + 32)} °F")
        st.write(f"Weather: {weather_data['weather'][0]['description'].capitalize()}")
        st.write(f"Humidity: {weather_data['main']['humidity']} %")
    xray_recorder.end_segment()
