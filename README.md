# gadgetbridge2mqtt
Docker container written in python to publish data stored in a Gadgetbridge database to MQTT. Also shared are a sample docker compose file, and a sample home assistant automation.  The automation uses broadcast intents to use the home assistant companion app to coordinate data transfer.

To do: It would be better to have the python code monitor for file changes on the database to execute the update.


Documentation:
Gadgetbridge Intents: https://gadgetbridge.org/internals/automations/intents/#intents
Home Assistant Broadcasting Intents: https://companion.home-assistant.io/docs/notifications/notification-commands/#broadcast-intent
Much of the python code for docker container taken from: https://github.com/Progaros/GadgetbridgeMqtt/blob/main/main.py#L292
although this code was itself (apparently) taken from an occasionally missing repo: https://git.olli.info/Oliver/GadgetbridgeMqtt.git


o What to do in Gadgetbridge app:
    o Settings (General, not device specific)
        o Automations
          o Choose an "Export location". If your phone is not rooted, you may have to create a new directory.
            Take note of it. Mine is something like /storage/emulated/0/Android/Android shared/Gadgetbridge.db
          o Turn on "Auto fetch activity data" for some maximum time to wait for downloading, maybe 3 hours? The
            automation will coordinate all the data transfers when the phone is available to HA and the server.
          o Set minimum time between fetches to 0 minutes.

        o Developer Options (necessary for HA automations to automatically fetch data)
          All the buttons below "Intent API" except "Allow Debug Commands" need to be enabled for the automation to work.

        o For all the bookkeeping to work, you need to input your birthday and name in Gadgetbridge under Settings -> About you.
          Distance measurement will be more accurate if you estimate step length and include height (presumably).

    o Device specific settings (gear icon in the watch):
      Open "Developer Settings". Two buttons need to be enabled for the HA automation to work: "Allow 3rd party apps to change settings"
      and "Allow GATT interaction through BLE Intent API"

o Settings in Home Assistant:

    o Notifications must be working on your phone. Unfortunately, that can be very phone specific, and change with updates. Many users
      rely unknowingly on using Google Services, which seems to be a default fallback for other problems. My phone has no Google Services,
      so I go to side panel Settings -> Companion App -> Services & devices, and click on the Home phone name, which is the only
      entry from my single server.  There I set Persistent Connection to "On home network only". Others use "Never". However, if you are using the minimal
      version of the app, then "Never" will not work. I cannot help you with this.

      Notifications are how HA talks to Gadgetbridge through the companion app.

    o side panel Settings -> Companion app -> Sensors: Manage sensors. Scroll down to "Last update sensor" and click on it. At the bottom of this menu
      there is a greyed out "Add new intent" button. Be sure to read the useful text above it. If you click on the radio button, it will immediately
      return to grey and create a new intent, with some default intent. Click on that new Intent to edit it, and replace the text with
      "nodomain.freeyourgadget.gadgetbridge.action.ACTIVITY_SYNC_FINISH". While here, create another intent with the text
      "nodomain.freeyourgadget.gadgetbridge.action.DATABASE_EXPORT_SUCCESS". In order to work, the companion app will need to be restarted.

      This allows for HA to listen if Gadgetbridge has successfully fetched data from your device, and then successfully exported it to the database.

o Copy database to server: I use syncthing to automate moving the database above to my server, so that I have a backup, and then I use this backup to
  feed my sensors to HA. There are other ways to do that. You could probably even leave it on your phone and read it using adb. Nextcloud might work?
  What you do with the database is up to you.

o Automation: I have written an automation script (automation.yaml) that checks if my phone is on the network, then (1) tells the phone to connect GB to the devices,
  (2) tells GB to fetch data from the devices, (3) wait for that to be performed successfully, (4) tells GB to export the db to the phone storage,
  (5) waits for confirmation that it succeded, and then sends a notification that it has completed, including how long it took. This last step is
  useful in debugging.

  Unfortunately, a couple of the steps in the automation use the device, which makes the yaml code incomprehensible, since it uses meaningless ID numbers
  instead of device names. So you need to replace these, or easier, just delete the condition in yaml and add it in the UI. You must also add the MAC
  address for the watch that you want to sync. Replace "ma:ca:dd:re:ss" with something like "AB:CD:12:34:56". You also need to replace
  "sensor.pixel_6a_last_update_trigger" and "notify.mobile_app_pixel_6a" with your phone's sensor and notification.


o Docker container:
  Sensors are published to HA through MQTT.  Updating is triggered by a "status" payload published on the topic "gadgetbridge/command"
  Shared is a docker-compose.yaml file that will spin up a
  docker container that takes the data from the Gadgetbridge database, and published it to MQTT so
  that Home Assistant will automatically discover it. It needs to know where to find the database
  that you have stored above. It also needs to know the details of your MQTT broker, the type of
  watch that you have (so how GB stores data in the database), and the MAC address of your device.
  If you have more than one device, you need to spin up a docker container for each one.


