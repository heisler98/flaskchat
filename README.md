docker build --tag squid-api .
docker run --publish 5001:5001 squid-api

note, use 5000 for prod and 50001 for dev
you must rebuild the image with any file changes