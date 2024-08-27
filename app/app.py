"""
PecNet
"""

import streamlit as st
import requests
import boto3 as aws
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
import mysql.connector

# Patch all supported libraries for X-Ray
patch_all()

# Initialize X-Ray recorder and add Streamlit middleware
xray_recorder.configure(service="PecNet")


# Database connection
def connect_to_db():
    xray_recorder.begin_subsegment("connect_to_db")
    ssm = aws.client("ssm")
    dbhost = ssm.get_parameter(Name="PecNetDBHost", WithDecryption=True)
    dbhost = dbhost["Parameter"]["Value"]
    dbuser = ssm.get_parameter(Name="PecNetDBUser", WithDecryption=True)
    dbuser = dbuser["Parameter"]["Value"]
    dbpassword = ssm.get_parameter(Name="PecNetDBPassword", WithDecryption=True)
    dbpassword = dbpassword["Parameter"]["Value"]

    dbconn = mysql.connector.connect(
        host=dbhost,
        user=dbuser,
        password=dbpassword,
        port=3306,
        database="channelpartnersdb",
    )
    xray_recorder.end_subsegment()
    return dbconn


def get_channel_partners(connection):
    xray_recorder.begin_subsegment("get_channel_partners")
    cursor = connection.cursor()
    cursor.execute("SELECT ChannelPartnerID, ChannelPartnerName FROM ChannelPartners")
    xray_recorder.end_subsegment()
    return cursor.fetchall()


def save_selected_partner(connection, partner_id):
    xray_recorder.begin_subsegment("save_selected_partner")
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO SelectedPartners (ChannelPartnerID) VALUES (%s)", (partner_id,)
    )
    connection.commit()
    xray_recorder.end_subsegment()


# Function to query and display selected partners
def get_selected_partners(connection):
    cursor = connection.cursor()
    query = """
    SELECT sp.ID, cp.ChannelPartnerName 
    FROM SelectedPartners sp
    JOIN ChannelPartners cp ON sp.ChannelPartnerID = cp.ChannelPartnerID
    """
    cursor.execute(query)
    return cursor.fetchall()


def get_api_key():
    """
    Retrieves the SSM Paramenter Store value for the API Key
    """
    xray_recorder.begin_subsegment("get_api_key_ssm")
    ssm = aws.client("ssm")
    parameter = ssm.get_parameter(Name="PecNetAppApiKey", WithDecryption=True)
    xray_recorder.end_subsegment()
    return parameter["Parameter"]["Value"]


# Function to get weather data
def get_weather(data):
    """
    Gets the current weather basted on the city value being passed
    """
    xray_recorder.begin_subsegment("get_weather_data")
    xray_recorder.put_metadata("user_query", data)
    api_key = get_api_key()
    if api_key == "N/A":
        st.error(
            "404 - The API Key is incorrect or not defined in the Parameter Store."
        )

    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": data, "appid": api_key, "units": "metric"}
    response = requests.get(base_url, params=params, timeout=5)
    xray_recorder.end_subsegment()
    return response.json()


def main():
    st.set_page_config(page_title="PecNet App", page_icon=":thermometer:")
    st.title("Channel Partner Selector")

    xray_recorder.begin_segment("PecNet")
    # Connect to the database
    connection = connect_to_db()

    # Fetch and display channel partners
    partners = get_channel_partners(connection)
    partner_names = {partner[1]: partner[0] for partner in partners}
    selected_partner_name = st.selectbox(
        "Select a Channel Partner", list(partner_names.keys())
    )

    # Save the selected partner
    if st.button("Save Selection"):
        selected_partner_id = partner_names[selected_partner_name]
        save_selected_partner(connection, selected_partner_id)
        st.success(f"Partner '{selected_partner_name}' saved successfully!")

    st.header("Saved Channel Partners")

    # Display saved channel partners
    selected_partners = get_selected_partners(connection)
    if selected_partners:
        st.write("Here are the partners that have been selected so far:")
        for partner in selected_partners:
            st.write(f"ID: {partner[0]}, Partner: {partner[1]}")
    else:
        st.write("No partners have been selected yet.")

    # Close the connection
    connection.close()

    st.title("Get Weather from OpenWeather.org")
    city_zip_code = st.text_input("Enter a city:")
    if st.button("Get Weather"):

        weather_data = get_weather(city_zip_code)
        if weather_data.get("cod") != 200:
            st.error(weather_data.get("cod"))
        else:
            st.write(f"City:  {weather_data['name']}")
            st.write(
                f"Temperature: {round((weather_data['main']['temp'] * 1.8) + 32)} °F"
            )
            st.write(
                f"Weather: {weather_data['weather'][0]['description'].capitalize()}"
            )
            st.write(f"Humidity: {weather_data['main']['humidity']} %")

    xray_recorder.end_segment()


if __name__ == "__main__":
    main()
