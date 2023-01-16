//Copy Right Manuel Maier & Michael Leitner 2019

/* Changes 15.05.2019 -ML-  :   + MAX31856 for Seebeck-Elements set to Gain 8 instead of Gain 32 & signal converted into Voltages according 
                                  to the factor R calculated for the individual voltage divider.
                                + temperature readings are stored as variables to be used in PID calculation
                                + code for PID controller is added.
   Changes 17.05.2019 -MCM- :   + Comments added 
     
   Changes 20.05.2019 -ML-  :   + Comments added regarding conversion of voltage mode readings
                                + Storage of temperature readings removed
                                
   Changes V3 01.06.2019 -ML- : + Logik umgekehrt-> kein Transistor mehr in der Schaltung für die Regelung: PWM wert=0 bedeuted MOSFET ist komplett geschlossen
                                + Filter für Temperaturstörungen 
                                + "Regelung auf Knopfdruck"
                                + Fault detection hinzugefügt  
   Changes V3 01.06.2019 -ML- : + Spannungsteiler: Widerstandswerte aktualisiert

   Changes V3 01.06.2019 -ML- : + Precooling element heizen statt kühlen
                                + PID Parameter Angepasst            
*/

#include <Adafruit_MAX31856.h>
#include <SPI.h>

#include <Wire.h>
#include <Adafruit_INA219.h>

#include <DPM8600.h>
DPM8600 converter;

//INA219 Addresses
//pre 0x42
//r1  0x43
//r2  0x45
//r3  0x44
//r4  0x41
//r5  0x40

Adafruit_INA219 ina219_pre(0x42);
Adafruit_INA219 ina219_r1(0x43);
Adafruit_INA219 ina219_r2(0x45);
Adafruit_INA219 ina219_r3(0x44);
Adafruit_INA219 ina219_r4(0x41);
Adafruit_INA219 ina219_r5(0x40);

float power_mW_pre = 0;
float power_mW_r1 = 0;
float power_mW_r2 = 0;
float power_mW_r3 = 0;
float power_mW_r4 = 0;
float power_mW_r5 = 0;

unsigned long time;

//Pins for PWM 
int PWM_pre = 7;
int PWM_r1 = 6;
int PWM_r2 = 5;
int PWM_r3 = 4;
int PWM_r4 = 3;
int PWM_r5 = 2;   


//Pins for button start PID control
const int buttonPin = 25;
const int ledPin = 50;

//Variables
float set_temperature = 25.00;
float PID_error_pre = 0;
float PID_error_r1 = 0;
float PID_error_r2 = 0;
float PID_error_r3 = 0;
float PID_error_r4 = 0;
float PID_error_r5 = 0;
float previous_error_pre = 0;
float previous_error_r1 = 0;
float previous_error_r2= 0;
float previous_error_r3= 0;
float previous_error_r4= 0;
float previous_error_r5= 0;
float elapsedTime, Time, timePrev;
float PID_value_pre = 0;
float PID_value_r1 = 0;
float PID_value_r2 = 0;
float PID_value_r3 = 0;
float PID_value_r4 = 0;
float PID_value_r5 = 0;
int PID_value_max = 150; //this needs to be adjusted depending on the maximum current of the power supply
float t_pre_previous;
float t_r1_previous;
float t_r2_previous;
float t_r3_previous;
float t_r4_previous;
float t_r5_previous;

//float t_r1p1=0;
//float t_r1p2=0;
//float t_r1p3=0;
//float t_r1p4=0;
//float t_r1p5=0;
//float t_r1p6=0;
//float t_r1p7=0;
//float t_r1p8=0;
//float t_r1p9=0;
//float t_r1p10=0;


int counter = 0;
int buttonReading_prev = LOW;
int buttonReading;
int state = LOW;
int control = 0;

String range;
String prev_range;
String PID_range = "coarse";

char Status;

//___________
const byte numChars = 32;
char receivedChars[numChars];
char tempChars[numChars];        // temporary array for use when parsing

      // variables to hold the parsed data
char messageFromPC[numChars] = {0};
int integerFromPC = 0;
float floatFromPC = 0.0;
float floatFromPC2 = 0.0;

boolean newData = false;

//___________



//PID constants
float kp_pre = 10;   float ki_pre = 0.26;   float kd_pre = 0;
float PID_p_pre = 0;    float PID_i_pre = 0;    float PID_d_pre = 0;  float PID_i_old_pre = 0;

float kp_r1 = 10;   float ki_r1 = 0.26;   float kd_r1 = 0;
float PID_p_r1 = 0;    float PID_i_r1 = 0;    float PID_d_r1 = 0;  float PID_i_old_r1 = 0;

float kp_r2 = 10;   float ki_r2 = 0.26;   float kd_r2 = 0;
float PID_p_r2 = 0;    float PID_i_r2 = 0;    float PID_d_r2 = 0;  float PID_i_old_r2 = 0;

float kp_r3 = 10;   float ki_r3 = 0.26;   float kd_r3 = 0;
float PID_p_r3 = 0;    float PID_i_r3 = 0;    float PID_d_r3 = 0;  float PID_i_old_r3 = 0;

float kp_r4 = 10;   float ki_r4 = 0.26;   float kd_r4 = 0;
float PID_p_r4 = 0;    float PID_i_r4 = 0;    float PID_d_r4 = 0;  float PID_i_old_r4 = 0;

float kp_r5 = 10;   float ki_r5 = 0.26;   float kd_r5 = 0;
float PID_p_r5 = 0;    float PID_i_r5 = 0;    float PID_d_r5 = 0;  float PID_i_old_r5 = 0;


// Use software SPI: CS, DI, DO, CLK

//Temp inlet A; J5
Adafruit_MAX31856 tc5 = Adafruit_MAX31856(A10, A0, A1, A2);

//Temp inlet B; J7
Adafruit_MAX31856 tc7 = Adafruit_MAX31856(A11, A0, A1, A2);

//Reactor temp outlet; J4
Adafruit_MAX31856 tc4 = Adafruit_MAX31856(A5, A0, A1, A2);

//Reactor temp precooling; J1
Adafruit_MAX31856 tc1 = Adafruit_MAX31856(A6, A0, A1, A2);

//Reactor temp plate 1; J2
Adafruit_MAX31856 tc2 = Adafruit_MAX31856(A4, A0, A1, A2);

//Reactor temp plate 2; J3
Adafruit_MAX31856 tc3 = Adafruit_MAX31856(A3, A0, A1, A2);

//Reactor temp plate 3; J6
Adafruit_MAX31856 tc6 = Adafruit_MAX31856(22, A0, A1, A2);

//Reactor temp plate 4; J8
Adafruit_MAX31856 tc8 = Adafruit_MAX31856(24, A0, A1, A2);

//Reactor temp plate 5; J9
Adafruit_MAX31856 tc9 = Adafruit_MAX31856(26, A0, A1, A2);

//ADS1115
//_____________________________________________________________________________________________________________
#include <Adafruit_ADS1015.h>
Adafruit_ADS1115 ads_1(0x48); /* Use this for the 16-bit version */
Adafruit_ADS1115 ads_2(0x49); /* Use this for the 16-bit version */

//16-Bit integer from Chip
int16_t adc1_0, adc1_1, adc1_2, adc1_3;
int16_t adc2_0, adc2_1, adc2_2, adc2_3;
//convert to float
float fadc1_0, fadc1_1, fadc1_2, fadc1_3;
float fadc2_0, fadc2_1, fadc2_2, fadc2_3;
//_____________________________________________________________________________________________________________

//Automatic calibration
float voltage = 0.0; 
float current = 0.0;
float a = 3;
float timediff = 0;
float timestemp = 0;

void setup() {

  // initialize the LED pin as an output:
  pinMode(ledPin, OUTPUT);
  // initialize the pushbutton pin as an input:
  pinMode(buttonPin, INPUT);

  pinMode(1, OUTPUT);
 
  // initialize serial communication and MAX31856 and set thermocouple type
  Serial.begin(9600);
  delay(3000);
  tc5.begin();
  tc5.setThermocoupleType(MAX31856_TCTYPE_T);
  tc1.begin();
  tc1.setThermocoupleType(MAX31856_TCTYPE_T);
  tc6.begin();
  tc6.setThermocoupleType(MAX31856_TCTYPE_T);
  tc2.begin();
  tc2.setThermocoupleType(MAX31856_TCTYPE_T);
  tc7.begin();
  tc7.setThermocoupleType(MAX31856_TCTYPE_T);
  tc3.begin();
  tc3.setThermocoupleType(MAX31856_TCTYPE_T);
  tc4.begin();
  tc4.setThermocoupleType(MAX31856_TCTYPE_T);
  tc8.begin();
  tc8.setThermocoupleType(MAX31856_TCTYPE_T);
  tc9.begin();
  tc9.setThermocoupleType(MAX31856_TCTYPE_T);

  //Voltage measurement with ADC as shown in the example code
  // The ADC input range (or gain) can be changed via the following
  // functions, but be careful never to exceed VDD +0.3V max, or to
  // exceed the upper and lower limits if you adjust the input range!
  // Setting these values incorrectly may destroy your ADC!
  //                                                                ADS1015  ADS1115
  //                                                                -------  -------
  ads_1.setGain(GAIN_TWOTHIRDS);   // 2/3x gain +/- 6.144V  1 bit = 3mV      0.1875mV (default)
  ads_2.setGain(GAIN_TWOTHIRDS);   // 2/3x gain +/- 6.144V  1 bit = 3mV      0.1875mV (default)
  // ads.setGain(GAIN_ONE);        // 1x gain   +/- 4.096V  1 bit = 2mV      0.125mV
  // ads.setGain(GAIN_TWO);        // 2x gain   +/- 2.048V  1 bit = 1mV      0.0625mV
  // ads.setGain(GAIN_FOUR);       // 4x gain   +/- 1.024V  1 bit = 0.5mV    0.03125mV
  // ads.setGain(GAIN_EIGHT);      // 8x gain   +/- 0.512V  1 bit = 0.25mV   0.015625mV
  // ads.setGain(GAIN_SIXTEEN);    // 16x gain  +/- 0.256V  1 bit = 0.125mV  0.0078125mV

  //Initialize the ads1115 chip
  ads_1.begin();
  ads_2.begin();

  analogWrite(PWM_pre,0);
  analogWrite(PWM_r1,0);
  analogWrite(PWM_r2,0);
  analogWrite(PWM_r3,0);
  analogWrite(PWM_r4,0);
  analogWrite(PWM_r5,0);  

  uint32_t currentFrequency;
      
  // Initialize the INA219.
  // By default the initialization will use the largest range (32V, 2A).  However
  // you can call a setCalibration function to change this range (see comments).
  if (! ina219_pre.begin()) {
    Serial.println("Failed to find INA219 chip pre");
    while (1) { delay(10); }
  }
  if (! ina219_r1.begin()) {
    Serial.println("Failed to find INA219 chip r1");
    while (1) { delay(10); }
  }
  if (! ina219_r2.begin()) {
    Serial.println("Failed to find INA219 chip r2");
    while (1) { delay(10); }
  }
  if (! ina219_r3.begin()) {
    Serial.println("Failed to find INA219 chip r3");
    while (1) { delay(10); }
  }
  if (! ina219_r4.begin()) {
    Serial.println("Failed to find INA219 chip r4");
    while (1) { delay(10); }
  }
  if (! ina219_r5.begin()) {
    Serial.println("Failed to find INA219 chip r5");
    while (1) { delay(10); }
  }

  // To use a slightly lower 32V, 1A range (higher precision on amps):
  //ina219.setCalibration_32V_1A();
  // Or to use a lower 16V, 400mA range (higher precision on volts and amps):
  //ina219.setCalibration_16V_400mA();
  ina219_pre.setCalibration_32V_1A();
  ina219_r1.setCalibration_32V_1A();
  ina219_r2.setCalibration_32V_1A();
  ina219_r3.setCalibration_32V_1A();
  ina219_r4.setCalibration_32V_1A();
  ina219_r5.setCalibration_32V_1A();

  // Initating power converter
  converter.begin(Serial);

  // Turn off power
  converter.power(false);
}

void loop() {
   
  float t_out = tc4.readThermocoupleTemperature();
  float t_r2 = tc3.readThermocoupleTemperature();
  float t_r1 = tc2.readThermocoupleTemperature();
  float t_pre = tc1.readThermocoupleTemperature();
  float t_in1 = tc5.readThermocoupleTemperature();
  float t_in2 = tc7.readThermocoupleTemperature();
  float t_r3 = tc6.readThermocoupleTemperature();
  float t_r4 = tc8.readThermocoupleTemperature();
  float t_r5 = tc9.readThermocoupleTemperature();

  //Read ADC sensor values
  adc1_0 = ads_1.readADC_SingleEnded(0);
  adc1_1 = ads_1.readADC_SingleEnded(1);
  adc1_2 = ads_1.readADC_SingleEnded(2);
  adc1_3 = ads_1.readADC_SingleEnded(3);

  adc2_0 = ads_2.readADC_SingleEnded(0);
  adc2_1 = ads_2.readADC_SingleEnded(1);
  adc2_2 = ads_2.readADC_SingleEnded(2);
  adc2_3 = ads_2.readADC_SingleEnded(3);

  //Convert to voltages
  fadc1_0 = adc1_0 * 0.1875; 
  fadc1_1 = adc1_1 * 0.1875;
  fadc1_2 = adc1_2 * 0.1875;
  fadc1_3 = adc1_3 * 0.1875;

  fadc2_0 = adc2_0 * 0.1875; 
  fadc2_1 = adc2_1 * 0.1875;
  fadc2_2 = adc2_2 * 0.1875;
  fadc2_3 = adc2_3 * 0.1875;

  power_mW_pre = ina219_pre.getPower_mW();
  power_mW_r1 = ina219_r1.getPower_mW();
  power_mW_r2 = ina219_r2.getPower_mW();
  power_mW_r3 = ina219_r3.getPower_mW();
  power_mW_r4 = ina219_r4.getPower_mW();
  power_mW_r5 = ina219_r5.getPower_mW();

//  // Filtern der "zufällig" auftretenden Temperatursprünge. Bei einer plötzlichen Abweichung von mehr als 3 °C wird dem Regelkreis der Wert aus der vorherigen Iteration übergeben.
//  if ( counter > 0) 
//    { if (abs(t_pre-t_pre_previous) > 3)
//    { t_pre = t_pre_previous; }
//      if (abs(t_r1-t_r1_previous) > 3)
//    { t_r1 = t_r1_previous; }
//      if (abs(t_r2-t_r2_previous) > 3)
//    { t_r2 = t_r2_previous; }}
  
  
  /*Konvertieren des vom MAX31856 gemessenen Spannungswertes. Durch den Spannungsteiler wurde die Ausgangsspannung der Seebeck-Elemente auf den Messbereich +-78.125mV begrenzt.
   * Rückrechnung auf wahre Ausgangsspannung durch Division durch den "R"-Wert des jeweiligen Spannungsteilers (Siehe KÜ). Der erste Teil der Gleichung liest den Wert den der Chip
   * gemessen hat aus und konvertiert in in eine Spannung. "tcxy.readThermocoupleTemperature()" gibt laut Datenblatt nur eine "19-bit Zahl" aus dem internen Register des Chips aus
   * (was auch immer das dann für eine Größe/Einheit ist) die durch die Division durch "(0.0078125*pow(2,17)*8*1.6)" erst in eine Spannung umgewandelt wird. Siehe Datenblatt MAX31856
   * Seite 20, letzte Tabellen-Zelle ganz unten.
   */
  float rhf_pre = adc1_0;
  float rhf1 = adc1_1;
  float rhf2 = adc1_2;
  float rhf3 = adc1_3;
  float rhf4 = adc2_0;
  float rhf5 = adc2_1;


  // Ausgabe über seriellen Monitor oder Plotter
  time = (millis()/1000);
  Serial.print(time);
  Serial.print("\t");
  Serial.print(set_temperature);
  Serial.print("\t");
  Serial.print(t_pre);
  Serial.print("\t");
  Serial.print(t_r1);
  Serial.print("\t");
  Serial.print(t_r2);
  Serial.print("\t");
  Serial.print(t_r3);
  Serial.print("\t");
  Serial.print(t_r4);
  Serial.print("\t");
  Serial.print(t_r5);
  Serial.print("\t");
  Serial.print(t_in1);
  Serial.print("\t");
  Serial.print(t_in2);
  Serial.print("\t");
  Serial.print(t_out);
  Serial.print("\t");
  Serial.print(rhf_pre);
  Serial.print("\t");
  Serial.print(rhf1);
  Serial.print("\t");
  Serial.print(rhf2);
  Serial.print("\t");
  Serial.print(rhf3);
  Serial.print("\t");
  Serial.print(rhf4);
  Serial.print("\t");
  Serial.print(rhf5);
  Serial.print("\t");
  Serial.print(PID_value_pre);
  Serial.print("\t");
  Serial.print(PID_value_r1);
  Serial.print("\t");
  Serial.print(PID_value_r2);
  Serial.print("\t");
  Serial.print(PID_value_r3);
  Serial.print("\t");
  Serial.print(PID_value_r4);
  Serial.print("\t");
  Serial.print(PID_value_r5);
  Serial.print("\t");
  Serial.print(power_mW_pre);
  Serial.print("\t");
  Serial.print(power_mW_r1);
  Serial.print("\t");
  Serial.print(power_mW_r2);
  Serial.print("\t");
  Serial.print(power_mW_r3);
  Serial.print("\t");
  Serial.print(power_mW_r4);
  Serial.print("\t");
  Serial.println(power_mW_r5);
  
    
  //_______________________________________________________________________________________________________________
  //Calculate the error between setpoint and real value


  // Aktueller Messwert wird für die nächste Iteration abgespeichert (für den Filter)
  t_pre_previous = t_pre;
  t_r1_previous = t_r1;
  t_r2_previous = t_r2;
  t_r3_previous = t_r3;
  t_r4_previous = t_r4;
  t_r5_previous = t_r5;

  // Start der Abfrage für die Regelung auf Kopfdruck
  buttonReading = digitalRead(buttonPin);
 
  recvWithStartEndMarkers();
    if (newData == true) {
        strcpy(tempChars, receivedChars);
            //   this temporary copy is necessary to protect the original data
            //   because strtok() used in parseData() replaces the commas with \0
        parseData();
        showParsedData();
        newData = false;
    }

    
  // check if the pushbutton is pressed. If it is, the buttonState is HIGH:
  if (buttonReading == HIGH && buttonReading_prev == LOW) {
    // turn LED on:
      PID_value_pre =0;
      PID_value_r1 =0;
      PID_value_r2 =0;
      PID_value_r3 =0;
      PID_value_r4 =0;
      PID_value_r5 =0;
      PID_p_pre = 0;
      PID_p_r1 = 0;
      PID_p_r2 = 0;
      PID_p_r3 = 0;
      PID_p_r4 = 0;
      PID_p_r5 = 0;
      PID_i_pre = 0;
      PID_i_r1 = 0;
      PID_i_r2 = 0;
      PID_i_r3 = 0;
      PID_i_r4 = 0;
      PID_i_r5 = 0;
      PID_d_pre = 0;
      PID_d_r1 = 0;
      PID_d_r2 = 0;
      PID_d_r3 = 0;
      PID_d_r4 = 0;
      PID_d_r5 = 0;
      previous_error_pre = 0;
      previous_error_r1 = 0;
      previous_error_r2 = 0;
      previous_error_r3 = 0;
      previous_error_r4 = 0;
      previous_error_r5 = 0;
      PID_i_old_pre = 0;
      PID_i_old_r1 = 0;
      PID_i_old_r2 = 0;
      PID_i_old_r3 = 0;
      PID_i_old_r4 = 0;
      PID_i_old_r5 = 0;
      Time = millis();
      
      
    if (state ==LOW){
      state = HIGH;
      digitalWrite(ledPin, state);
      control = 1;
    }
    else {
     state = LOW;
     control = 0;
     digitalWrite(ledPin, state);
     analogWrite(PWM_pre,PID_value_pre);
     analogWrite(PWM_r1,PID_value_r1);
     analogWrite(PWM_r2,PID_value_r2);
     analogWrite(PWM_r3,PID_value_r3);
     analogWrite(PWM_r4,PID_value_r4);
     analogWrite(PWM_r5,PID_value_r5);  
    }
  }

  // State kann High (LED ein) oder Low sein
  digitalWrite(ledPin, state);
  buttonReading_prev = buttonReading;
  
  // Solange die Variable "control" gleich 0 ist, bleibt die Regelung inaktiv
  if (control == 0){    
  }
  
  // Wenn controll=1, start der Regelung
  else {
//    t_r1p10=t_r1p9;
//    t_r1p9=t_r1p8;
//    t_r1p8=t_r1p7;
//    t_r1p7=t_r1p6;
//    t_r1p6=t_r1p5;
//    t_r1p5=t_r1p4;
//    t_r1p4=t_r1p3;
//    t_r1p3=t_r1p2;
//    t_r1p2=t_r1p1;
//    t_r1p1=t_r1;
        
    PID_error_pre = (t_pre-set_temperature); //Heizen (rot auf +, schwarz auf Erde)
    PID_error_r1 = (t_r1-set_temperature);
    PID_error_r2 = (t_r2-set_temperature);
    PID_error_r3 = (t_r3-set_temperature);
    PID_error_r4 = (t_r4-set_temperature);
    PID_error_r5 = (t_r5-set_temperature);
     
    //Calculate proportional value
    PID_p_pre = PID_error_pre;
    PID_p_r1 = PID_error_r1;
    PID_p_r2 = PID_error_r2;
    PID_p_r3 = PID_error_r3;
    PID_p_r4 = PID_error_r4;
    PID_p_r5 = PID_error_r5;
  
    //Calculate derivative
    timePrev = Time;                            // the previous time is stored before the actual time read
    Time = millis();                            // actual time read
    elapsedTime = (Time - timePrev)/1000;
    
    //Calculate I value and sum past values
    PID_i_pre = PID_i_old_pre + (PID_error_pre*elapsedTime);
    PID_i_old_pre = PID_i_pre;
    PID_i_r1 = PID_i_old_r1 + (PID_error_r1*elapsedTime);
    PID_i_old_r1 = PID_i_r1;
    PID_i_r2 = PID_i_old_r2 + (PID_error_r2*elapsedTime);
    PID_i_old_r2 = PID_i_r2;
    PID_i_r3 = PID_i_old_r3 + (PID_error_r3*elapsedTime);
    PID_i_old_r3 = PID_i_r3;
    PID_i_r4 = PID_i_old_r4 + (PID_error_r4*elapsedTime);
    PID_i_old_r4 = PID_i_r4;
    PID_i_r5 = PID_i_old_r5 + (PID_error_r5*elapsedTime);
    PID_i_old_r5 = PID_i_r5;
  
    //Calculate derivative
    PID_d_pre = ((PID_error_pre - previous_error_pre)/elapsedTime);
    PID_d_r1 = ((PID_error_r1 - previous_error_r1)/elapsedTime);
    PID_d_r2 = ((PID_error_r2 - previous_error_r2)/elapsedTime);
    PID_d_r3 = ((PID_error_r3 - previous_error_r3)/elapsedTime);
    PID_d_r4 = ((PID_error_r4 - previous_error_r4)/elapsedTime);
    PID_d_r5 = ((PID_error_r5 - previous_error_r5)/elapsedTime);
    
    //Summation of P + I + D with constants
    PID_value_pre = PID_p_pre * kp_pre + PID_i_pre * ki_pre + PID_d_pre * kd_pre;
    PID_value_r1 = PID_p_r1 * kp_r1 + PID_i_r1 * ki_r1 + PID_d_r1 * kd_r1;
    PID_value_r2 = PID_p_r2 * kp_r2 + PID_i_r2 * ki_r2 + PID_d_r2 * kd_r2;
    PID_value_r3 = PID_p_r3 * kp_r3 + PID_i_r3 * ki_r3 + PID_d_r3 * kd_r3;
    PID_value_r4 = PID_p_r4 * kp_r4 + PID_i_r4 * ki_r4 + PID_d_r4 * kd_r4;
    PID_value_r5 = PID_p_r5 * kp_r5 + PID_i_r5 * ki_r5 + PID_d_r5 * kd_r5;
  
    //Ausgabe nur von 0-5V möglich; wenn PID_value negativ wird sollte das Peltier-element umgepolt werden 
    //von Kühlen auf Heizen bzw umgekehrt je nachdem wie das Element angeschlossen ist
    //Man könnte auch die Range beschränken, damit der MOSFET nicht komplett öffnet. PID_value max 150 oder so
    //Das müssten wir dann auch machen, wenn unser Netzteil mehr als 5A liefert
    //We define PWM range between 0 and 255
    if(PID_value_pre < 0)
      {    PID_value_pre = 0;    }
    if(PID_value_pre > PID_value_max)  
      {    PID_value_pre = PID_value_max;  }
    if(PID_value_r1 < 0)
      {    PID_value_r1 = 0;    }
    if(PID_value_r1 > PID_value_max)  
      {    PID_value_r1 = PID_value_max;  } 
    if(PID_value_r2 < 0)
      {    PID_value_r2 = 0;    }
    if(PID_value_r2 > PID_value_max)  
      {    PID_value_r2 = PID_value_max;  }
    if(PID_value_r3 < 0)
      {    PID_value_r3 = 0;    }
    if(PID_value_r3 > PID_value_max)  
      {    PID_value_r3 = PID_value_max;  }
    if(PID_value_r4 < 0)
      {    PID_value_r4 = 0;    }
    if(PID_value_r4 > PID_value_max)  
      {    PID_value_r4 = PID_value_max;  }
    if(PID_value_r5 < 0)
      {    PID_value_r5 = 0;    }
    if(PID_value_r5 > PID_value_max)  
      {    PID_value_r5 = PID_value_max;  }
      
    //Write PWM signal to the mosfet on digital pin 
    analogWrite(PWM_pre,PID_value_pre);
    analogWrite(PWM_r1,PID_value_r1);
    analogWrite(PWM_r2,PID_value_r2);
    analogWrite(PWM_r3,PID_value_r3);
    analogWrite(PWM_r4,PID_value_r4);
    analogWrite(PWM_r5,PID_value_r5);
    
    //Store the previous error for next loop.
    previous_error_pre = PID_error_pre;    
    previous_error_r1 = PID_error_r1;
    previous_error_r2 = PID_error_r2;
    previous_error_r3 = PID_error_r3;
    previous_error_r4 = PID_error_r4;
    previous_error_r5 = PID_error_r5;
  }
   
  //_______________________________________________________________________________________________________________

  // This will make a rampe as the user defined it. The ramp starts from the user defined voltage until the defined current
  if (a == 2){
    //Start continuous increase
    timestemp = time;
    timediff = 60*10;
    a = 1;
  }
  if (time >= timestemp + timediff && timestemp !=0 ){
    voltage = voltage + 0.2;
    timestemp = time;
    a = 1;
  }
  // This turns on the power supply at a specific voltage and current as the user defined them
  if (a == 1){
    // Turn on the power
    converter.writeVC(voltage, current);
    delay(10);
    converter.power(true);
  }
  // This turns off the power supply and also sets a specific voltage and current as the user defined them
  if (a == 0){
    // Turn off the power
    converter.writeVC(voltage, current);
    delay(10);
    converter.power(false);
    timestemp = 0;
  }

  a = 3;
 
  counter++;
}


//_______________________________________________________________________________________________________________

void recvWithStartEndMarkers() {
    static boolean recvInProgress = false;
    static byte ndx = 0;
    char startMarker = '<';
    char endMarker = '>';
    char rc;

    while (Serial.available() > 0 && newData == false) {
        rc = Serial.read();

        if (recvInProgress == true) {
            if (rc != endMarker) {
                receivedChars[ndx] = rc;
                ndx++;
                if (ndx >= numChars) {
                    ndx = numChars - 1;
                }
            }
            else {
                receivedChars[ndx] = '\0'; // terminate the string
                recvInProgress = false;
                ndx = 0;
                newData = true;
            }
        }

        else if (rc == startMarker) {
            recvInProgress = true;
        }
    }
}

//_______________________________________________________________________________________________________________

void parseData() {      // split the data into its parts

    char * strtokIndx; // this is used by strtok() as an index

    strtokIndx = strtok(tempChars,",");      // get the first part - the string
    strcpy(messageFromPC, strtokIndx);       // copy it to messageFromPC
          
    strtokIndx = strtok(NULL, ",");     // this continues where the previous call left off
    floatFromPC = atof(strtokIndx);     // convert this part to a float

    strtokIndx = strtok(NULL, ",");     // this continues where the previous call left off
    floatFromPC2 = atof(strtokIndx);   // convert this part to a float
    
    if (messageFromPC[0] == '1') {
      buttonReading = HIGH;
      buttonReading_prev = LOW;
      state = LOW;

      set_temperature = floatFromPC;
    }
    
    if (messageFromPC[0] == '0') {
      buttonReading = HIGH;
      buttonReading_prev = LOW;
      state = HIGH;

      set_temperature = floatFromPC;
    } 

    if (messageFromPC[0] == '2') {
      a = 2;
      voltage = floatFromPC;
      current = floatFromPC2;
    } 

    if (messageFromPC[0] == '3') {
      a = 1;
      voltage = floatFromPC;
      current = floatFromPC2;
    }
    
    if (messageFromPC[0] == '4') {
      a = 0;
      voltage = floatFromPC;
      current = floatFromPC2;
    } 
}

//_______________________________________________________________________________________________________________

void showParsedData() {
    
    if (messageFromPC[0] == '1'){
      Serial.println("Regulation on");
      Serial.print("Set Temperature ");
      Serial.println(floatFromPC);
    }
    if (messageFromPC[0] == '0'){
      Serial.println("Regulation off");
      Serial.print("Set Temperature ");
      Serial.println(floatFromPC);
    }
    if (messageFromPC[0] == '3'){
      Serial.println("Regulation on");
      Serial.print("Set Voltage ");
      Serial.println(floatFromPC);
      Serial.print("Set Current ");
      Serial.println(floatFromPC2);
    }
    if (messageFromPC[0] == '4'){
      Serial.println("Regulation off");
      Serial.print("Set Voltage ");
      Serial.println(floatFromPC);
      Serial.print("Set Current ");
      Serial.println(floatFromPC2);
    }
    if (messageFromPC[0] == '2'){
      Serial.println("Regulation on (ramp)");
      Serial.print("Set Voltage ");
      Serial.println(floatFromPC);
      Serial.print("Set Current ");
      Serial.println(floatFromPC2);
    }
}
