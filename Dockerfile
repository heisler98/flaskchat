# set base image (host OS)
FROM python:3.9

# set the working directory in the container
WORKDIR /flaskchat
COPY . .

# install dependencies
RUN pip install -r requirements.txt

# command to run on container start
CMD [ "python", "./main.py" ] 