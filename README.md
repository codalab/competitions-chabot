# competitions-chabot

Create a new .env file from the .env_sample:
```shell script
cp .env_sample .env
```

Make sure to change the Heroku API key and the Special Secret to appropriate values

Then run the app
```shell script
python app.py # TODO: run using wsgi
```

Use serveo to open up port the FLASK_PORT from the .env file.
```shell script
ssh -R chabot:80:localhost:<this should match FLASK_PORT> serveo.net
```
