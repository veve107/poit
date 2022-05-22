float value = 5;
int setting = 0;
void setup()
{
  pinMode(8, OUTPUT);
  Serial.begin(9600);
}

void loop(){
  float n1 = (float)analogRead(A7)*5/1023;

  if(n1 > 4.5){
    setting = 0;
  }else if(n1 < 0.1 ){
    setting = 1;  
  }
  
  delay(100);
  if(setting){
    digitalWrite(8, HIGH);  
  }else{
    digitalWrite(8, LOW);
  }
  delay(100);
  Serial.println(n1);
}
