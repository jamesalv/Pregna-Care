#include <WiFi.h>
#include <HTTPClient.h>
#include "MAX30105.h"
#include "heartRate.h"
#include <OneWire.h>
#include <DallasTemperature.h>
#include "spo2_algorithm.h"


const char* ssid = "BETON MAS 185";
const char* password = "mikhael0303";
int httpResponseCode;

//Your Domain name with URL path or IP address with path
const char* serverName = "http://20.81.131.50:8080/upload";

MAX30105 particleSensor;

const byte RATE_SIZE = 4; //Increase this for more averaging. 4 is good.
byte rates[RATE_SIZE]; //Array of heart rates
byte rateSpot = 0;
long lastBeat = 0; //Time at which the last beat occurred
float beatsPerMinute;
int beatAvg;

int tcounter =0;
int counter = 0;
int beatSum = 0;
double temperatureSum = 0;
double spo2Sum = 0;
int beatToSend = 0;
double temperatureToSend = 0;
double spo2ToSend = 0;

double avered = 0;
double aveir = 0;
double sumirrms = 0;
double sumredrms = 0;

double SpO2 = 0; //SPO2 value
double ESpO2 = 0;//SPO2 value minimum
double FSpO2 = 0.7; //filter factor for estimated SpO2
double frate = 0.95; //low pass filter for IR/red LED value to eliminate AC component
double temperatureC = 0;
double tempFromMax = 0; 
int i = 0;
int Num = 30;
#define FINGER_ON 7000   
#define MINIMUM_SPO2 90.0 

int Tonepin = 4; 

// GPIO where the DS18B20 is connected to
const int oneWireBus = 4;     

// Setup a oneWire instance to communicate with any OneWire devices
OneWire oneWire(oneWireBus);

// Pass our oneWire reference to Dallas Temperature sensor 
DallasTemperature sensors(&oneWire);

TaskHandle_t dordor;
TaskHandle_t Temperature;

void setup() {
  Serial.begin(115200);

  WiFi.begin(ssid, password);
  Serial.println("Connecting");
  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to WiFi network with IP Address: ");
  Serial.println(WiFi.localIP());

  // Start the DS18B20 sensor
  sensors.begin();

  Serial.println("System Start");

  // Initialize sensor
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) //Use default I2C port, 400kHz speed
  {
    Serial.println(F("MAX30102 was not found. Please check wiring/power."));
    while (1);
  }

  xTaskCreatePinnedToCore(
  dorAPI,   /* Task function. */
  "nmebak API",     /* name of task. */
  10000,       /* Stack size of task */
  NULL,        /* parameter of the task */
  3,           /* priority of the task */
  &dordor,      /* Task handle to keep track of created task */
  0);          /* pin task to core 0 */                  
  delay(500); 

  xTaskCreatePinnedToCore(
  TemperatureCode,   /* Task function. */
  "Temperature",     /* name of task. */
  10000,       /* Stack size of task */
  NULL,        /* parameter of the task */
  3,           /* priority of the task */
  &Temperature,      /* Task handle to keep track of created task */
  0);          /* pin task to core 1 */
  delay(500);

  byte ledBrightness = 0x7F; // Options: 0=Off to 255=50mA
  byte sampleAverage = 4; //Options: 1, 2, 4, 8, 16, 32
  byte ledMode = 3; //Options: 1 = Red only(心跳), 2 = Red + IR(血氧)
  int sampleRate = 800; //Options: 50, 100, 200, 400, 800, 1000, 1600, 3200
  int pulseWidth = 215; //Options: 69, 118, 215, 411
  int adcRange = 16384; //Options: 2048, 4096, 8192, 16384
  // Set up the wanted parameters
  particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange); //Configure sensor with these settings
  particleSensor.enableDIETEMPRDY();

  particleSensor.setPulseAmplitudeRed(0x0A); //Turn Red LED to low to 
}

void bpmCode(){
  long irValue = particleSensor.getIR();    //Reading the IR value it will permit us to know if there's a finger on the sensor or not
  if (irValue > FINGER_ON ) {
     if (checkForBeat(irValue) == true) {
      long delta = millis() - lastBeat;
      lastBeat = millis();
      beatsPerMinute = 60 / (delta / 1000.0);
      if (beatsPerMinute < 255 && beatsPerMinute > 20) {
        
        rates[rateSpot++] = (byte)beatsPerMinute;
        rateSpot %= RATE_SIZE;
        beatAvg = 0;
        for (byte x = 0 ; x < RATE_SIZE ; x++) beatAvg += rates[x];
        beatAvg /= RATE_SIZE;
      }
    }

    uint32_t ir, red ;
    double fred, fir;
    particleSensor.check(); //Check the sensor, read up to 3 samples
    if (particleSensor.available()) {
      i++;
      ir = particleSensor.getFIFOIR(); 
      red = particleSensor.getFIFORed(); 
      //Serial.println("red=" + String(red) + ",IR=" + String(ir) + ",i=" + String(i));
      fir = (double)ir;//double
      fred = (double)red;//double
      aveir = aveir * frate + (double)ir * (1.0 - frate); //average IR level by low pass filter
      avered = avered * frate + (double)red * (1.0 - frate);//average red level by low pass filter
      sumirrms += (fir - aveir) * (fir - aveir);//square sum of alternate component of IR level
      sumredrms += (fred - avered) * (fred - avered); //square sum of alternate component of red level

      if ((i % Num) == 0) {
        double R = (sqrt(sumirrms) / aveir) / (sqrt(sumredrms) / avered);
        SpO2 = -23.3 * (R - 0.4) + 100;
        ESpO2 = FSpO2 * ESpO2 + (1.0 - FSpO2) * SpO2;//low pass filter
        if (ESpO2 <= MINIMUM_SPO2) ESpO2 = MINIMUM_SPO2; //indicator for finger detached
        if (ESpO2 > 100) ESpO2 = 99.9;
        //Serial.print(",SPO2="); Serial.println(ESpO2);
        sumredrms = 0.0; sumirrms = 0.0; SpO2 = 0;
        i = 0;
      }
      particleSensor.nextSample(); //We're finished with this sample so move to next sample
    }
  }
  else {
    for (byte rx = 0 ; rx < RATE_SIZE ; rx++) rates[rx] = 0;
    beatAvg = 0; rateSpot = 0; lastBeat = 0;
    avered = 0; aveir = 0; sumirrms = 0; sumredrms = 0;
    SpO2 = 0; ESpO2 = 0;
   }
}

void TemperatureCode( void * pvParameters ){
  for(;;){
    sensors.requestTemperatures(); 
    temperatureC = sensors.getTempCByIndex(0);
    delay(100);
  }
}

void dorAPI(void* pvParameters){
  for(;;){
    WiFiClient client;
    HTTPClient http;
  
    // Your Domain name with URL path or IP address with path
    http.begin(client, serverName);

    http.addHeader("Content-Type", "application/json");
    char postString[150];
    if(counter != 0){
      temperatureToSend = temperatureSum / tcounter;
      beatToSend = beatSum / counter;
      spo2ToSend = spo2Sum / counter;\
      sprintf(postString, "{\"body_temperature\":%.2lf,\"spo2\":%.2lf, \"heart_rate\":%d}",temperatureToSend, spo2ToSend, beatToSend);
      httpResponseCode = http.POST(postString);
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);
      Serial.println(postString);
    }
    beatToSend = temperatureToSend = spo2ToSend = beatSum = temperatureSum = spo2Sum = tcounter = counter = 0;
    delay(10000);
  }

}

void loop(){
  bpmCode();
  // Serial.print("Bpm:" + String(beatAvg));  
  // if (beatAvg > 30)  Serial.println(",SPO2:" + String(ESpO2) + " ");
  // else Serial.println(",SPO2:" + String(ESpO2) + " ");
  // Serial.print(temperatureC);
  // Serial.println("ºC ");
  if(beatAvg != 0 && ESpO2 != 0){
    counter++;
    beatSum += beatAvg;
    spo2Sum += ESpO2;
  }
  if(temperatureC >= 0){
    tcounter++;
    temperatureSum += temperatureC;
  }
}


