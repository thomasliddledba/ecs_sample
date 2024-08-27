# Use the official lightweight Python image
FROM public.ecr.aws/docker/library/python:3.11.6-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy the application files
COPY app/app.py .
RUN rm -rf .apikey

# Expose the port the Streamlit app runs on
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
