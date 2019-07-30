# competitions-chabot

Create a new .env file from the .env_sample:
```shell script
cp .env_sample .env
```
Make sure to change the Heroku API key and the Special Secret to their appropriate values

Then run the app
```shell script
docker-compose up -d
```

Use serveo and autossh to open the FLASK_PORT from the .env file and keep it open.
```shell script
autossh -R chabot:80:localhost:<this should match FLASK_PORT> serveo.net
```
