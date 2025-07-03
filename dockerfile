# Dockerfile - Specifies a custom runtime environment with Google Chrome

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for headless Chrome and its driver
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    --no-install-recommends

# Install Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y google-chrome-stable

# Install the correct version of Chromedriver
RUN CHROME_DRIVER_VERSION=$(wget -q -O - "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE") \
    && wget -q --continue -P /usr/local/bin/ "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_DRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip /usr/local/bin/chromedriver-linux64.zip -d /usr/local/bin/ \
    && rm /usr/local/bin/chromedriver-linux64.zip \
    && mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Define the command to run the function
CMD ["functions-framework", "--target=automated_zerodha_login", "--port=8080"]
