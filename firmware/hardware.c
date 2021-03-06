#include <avr/io.h>
#include <avr/wdt.h>	// Watchdog timer configuration functions.
#include <avr/power.h>	// Clock prescaler configuration functions.
#include <avr/interrupt.h>
#include <string.h>
#include <stdio.h>
#include <util/delay.h>


#include <LUFA/Drivers/USB/USB.h>
#include <LUFA/Platform/Platform.h>

#include "hardware.h"
#include "lib/uart.h"	// Include the updated version of Peter Fleurys UART lib.

//Set F_CPU as well if not set in makefile. Needed for baud calculation.
#ifndef F_CPU
	#define F_CPU	16000000
#endif
// Define baut rate.
#define UART_BAUD_RATE	9600  
		


// *****************************************************************************
// Function: configure hardware. ***********************************************
// *****************************************************************************
void setupHardware(void)
{	
	// Disable watchdog if enabled by bootloader/fuses. ***********************
	MCUSR &= ~(1 << WDRF);
	wdt_disable();
	
	
	// Configure outputs. *****************************************************
	
	// Configure LEDs. Active high.
	// Additional LEDs.
	// Orange.
	LED1DDR |= (1 << LED1PIN);
	LED1PORT &= ~(1 << LED1PIN);	//OFF
	// Green.
	LED2DDR |= (1 << LED2PIN);
	LED2PORT &= ~(1 << LED2PIN);	//OFF
	
	// Onboard LEDs.
	// Orange.
	LED1ONBOARDDDR |= (1 << LED1ONBOARDPIN);
	LED1ONBOARDPORT |= (1 << LED1ONBOARDPIN);	//OFF
	// Green.
	LED2ONBOARDDDR |= (1 << LED2ONBOARDPIN);
	LED2ONBOARDPORT |= (1 << LED2ONBOARDPIN);	//OFF
	
	// Configure camera trigger pin. Active high.
	CAMDDR |= (1 << CAMPIN);
	CAMPORT &= ~(1 << CAMPIN);	//OFF


	// Stepper ports. Step on rising edge, enable active low.
	// Build stepper enable.
	BUILDENABLEDDR |= (1 << BUILDENABLEPIN);
	BUILDENABLEPORT &= ~(1 << BUILDENABLEPIN);	// Disabled...
	// Build stepper direction.
	BUILDDIRDDR |= (1 << BUILDDIRPIN);
	BUILDDIRPORT |= (1 << BUILDDIRPIN);
	// Build stepper clock.
	BUILDCLOCKDDR |= (1 << BUILDCLOCKPIN);
	BUILDCLOCKPORT &= ~(1 << BUILDCLOCKPIN);
	
	// Tilt stepper enable.	Active high.
	TILTENABLEDDR |= (1 << TILTENABLEPIN);
	TILTENABLEPORT &= ~(1 << TILTENABLEPIN);	// Disabled...
	// Beamer stepper direction.
	TILTDIRDDR |= (1 << TILTDIRPIN);
	TILTDIRPORT |= (1 << TILTDIRPIN);
	// Beamer stepper clock.
	TILTCLOCKDDR |= (1 << TILTCLOCKPIN);
	TILTCLOCKPORT &= ~(1 << TILTCLOCKPIN);		// Low...
	
	// Configure servo port as output.
	SERVODDR |= (1 << SERVOPIN);
	//SERVOPORT |= (1 << SERVOPIN);
	

	// Configure inputs. ******************************************************
	
	// Limit switches using internal pull-ups. Configured as inputs by default.
	LIMITBUILDTOPPORT |= (1 << LIMITBUILDTOPPIN);		// Build platform top.
	LIMITBUILDBOTTOMPORT |= (1 << LIMITBUILDBOTTOMPIN);	// Build platform bottom.
	LIMITTILTPORT |= (1 << LIMITTILTPIN);				// Tilt.

	// Configure INT1--3 to fire on falling edge.
	EICRA |= (1 << ISC11 | 1 << ISC10 | 1 << ISC01 | 1 << ISC00);	// Fire on rising edge. Datasheed p. 86.
	EICRB |= (1 << ISC61 | 1 << ISC60);
	EIMSK |= (1 << INT6 | 1 << INT1 | 1 << INT0);

	// Configure PCINT4 for tilt.
//	PCICR |= (1 << PCIE0);
//	PCMSK0 |= (1 << PCINT4);
	

	// Configure timer0. Call ISR every 0,1 ms. *******************************
	// Prescaler:	16.000.000 Hz / 8 = 2.000.000 Hz
  	//			1 s / 2.000.000 = 0,0000005 s per clock cycle.
  	// Clock cycles per millisecond:
  	//			0,001 s / 0,0000005 s = 2.000 clock cycles per millisecond.
  	//			Overflow at 200 clock cycles comes every 0,1 ms.
  	TCCR0A |= (1 << WGM01);	// CTC mode. Data sheet page 104.
  	TCCR0B |= (1<<CS01);	// Set prescaler to 8. Data sheet page 106.
  	OCR0A = 200;			// Set channel A compare value.
  	TIMSK0 |= (1<<OCIE0A);	// Enable channel A compare interrupt.


	// Stepper PWM for beamer drive. ******************************************
	// Configure timer1 for CTC with output toggle on OC1A and interrupt. Prescaler 1.
	TCCR1A |= (1 << COM1A0);		// Toggle OC1A on compare match.
	TCCR1B |= (1 << WGM12);			// CTC with OCR1AH/OCR1AL compare registers. Data sheet page 130.
//	TCCR1B |= (1 << CS10);			// Set prescaler to 1. Datasheet page 133.				Do this later...
	TIMSK1 |= (1 << OCIE1A);		// Enable channel A CTC interrupt. Datasheet p. 136.



	// Stepper PWM for build platform drive. **********************************
	// Configure timer3 for CTC with interrupt on compare match. Prescaler 1.
	TCCR3A |= (1 << COM3A0);		// Toggle OC3A on compare match.
	TCCR3B |= (1 << WGM32);		// CTC with OCR3AH/OCR3AL compare registers. Data sheet page 130.
//	TCCR3B |= (1 << CS30);		// Set prescaler to 1. Datasheet page 133. 				DO NOT ENABLE BY DEFAULT!
	TIMSK3 |= (1 << OCIE3A);		// Enable channel A CTC interrupt. Datasheet p. 136.
	
	
/*		// Servo PWM. *************************************************************
	// Configure timer3 for CTC with interrupt on compare match. Prescaler 8.
	TCCR3B |= (1 << WGM32);		// CTC with OCR3AH/OCR3AL compare registers. Data sheet page 130.
//	TCCR3B |= (1 << CS31);		// Set prescaler to 8. Datasheet page 133. Do this in main...
	TIMSK3 |= (1<<OCIE3A);		// Enable channel A CTC interrupt. Datasheet p. 136.
	SERVODDR |= (1 << SERVOPIN);	// Set OC3A as output.
*/	
	
	// Servo PWM for shutter. *************************************************
	// Configure timer4 in 8 bit mode without CTC.
	// Set servo signal pin high on timer overflow interrupt, wait for
	// compare match interrupt and set pin low again.
	//Do this later.	TCCR4B |= (1 << CS43);				// Prescaler 128. Datasheet p 166.
	TIMSK4 |= (1 << OCIE4D | 1 << TOIE4);	// Enable channel D compare match interrupt and counter overflow interrupt.
	
	
	/*
	// TIMER 4 IS A BITCH!
	// SUPPOSEDLY ONLY OCR4C CAN SERVE AS TOP THAT RESETS ON COMPARE MATCH! Datasheet p 149 under Normal Mode.
	// Thus, make sure to set OCR4A slightly below OCR4C at the same time to use OC4A output pin.
	// This will fire an interrupt on OCR4A and reset the counter on OCR4C compare match.
	// TODO: why not simply reset the counter manually on OCR4A?
	// Configure timer4 in 8 bit mode for CTC with interrupt on compare match.
	TCCR4A |= (1 << COM4A0);				// Toggle OC4A on compare match. Datasheet p 162.
	TCCR4B |= (1 << CS42);				// Prescaler 8. Datasheet p 166.
	TIMSK4 |= (1 << OCIE4A);
	*/
	
	
	// Initialise UART using uart.c function.
	// This calculates the baud interval and passes it to the init function.
	// Don't forget to enable interrupts later on...
	uart1_init( UART_BAUD_SELECT(UART_BAUD_RATE,F_CPU) );
	
	
	
	// Inititalise USB using LUFA function. ***********************************
	// Disable the VUSB pad to mend an issue with the Caterina bootloader not
	// exiting USB connection correctly.
	// See here: http://www.avrfreaks.net/forum/running-lufa-projects-leonardo
	USBCON &= ~(1 << OTGPADE);
	USB_Init();
	
	// Initialise LCD. ********************************************************
//	lcd_init(0x0C);		// LCD on, cursor off: see lcd.h.
//	lcd_clrscr();		// Clear and set cursor to home.
	
	// Initialise button. *****************************************************
//	buttonInit();
	
	// Initialise rotary encoder. *********************************************
//	rotaryEncoderInit();
	
}



// Define functions to set timer1 and timer3 compare values (two 8 bit registers OCR1AH / OCR1AL ).
// See data sheet p 110 for 16 bit register access.
// Function is needed to make sure that no interrupt kicks in between writing the two 8 bit registers.
void timer1SetCompareValue( uint16_t input )
{
	// Save global interrupt flag.
	uint8_t sreg;
	sreg = SREG;
	// Disable interrupts.
	cli();
	//Set TCNTn to input.
	OCR1A = input;
	// Restore global interrupt flag
	SREG = sreg;	// Makes sei() unneccessary.
}

void timer3SetCompareValue( uint16_t input )
{
	// Save global interrupt flag.
	uint8_t sreg;
	sreg = SREG;
	// Disable interrupts.
	cli();
	//Set TCNTn to input.
	OCR3A = input;
	// Restore global interrupt flag.
	SREG = sreg;	// Makes sei() unneccessary.
}

void timer4SetCompareValue( uint8_t input )
{
// NOTE: For timer 4 only OCR4C generates a reset on compare match, but only channels A, B and D have an interrupt...
//	// Save global interrupt flag.
//	uint8_t sreg;
//	sreg = SREG;
//	// Disable interrupts.
//	cli();
//	//Set TCNTn to input.
	//OCR4A = input-5;
	//OCR4C = input;
	OCR4D = input;
//	// Restore global interrupt flag.
//	SREG = sreg;	// Makes sei() unneccessary.
}

void ledYellowOn( void )
{
	LED1ONBOARDPORT &= ~(1 << LED1ONBOARDPIN);
	LED1PORT |= (1 << LED1PIN);
}

void ledYellowOff( void )
{
	LED1ONBOARDPORT |= (1 << LED1ONBOARDPIN);
	LED1PORT &= ~(1 << LED1PIN);
}

void ledYellowToggle( void )
{
	LED1ONBOARDPORT ^= (1 << LED1ONBOARDPIN);
	LED1PORT ^= (1 << LED1PIN);
}

void ledGreenOn( void )
{
	LED2ONBOARDPORT &= ~(1 << LED2ONBOARDPIN);
	LED2PORT |= (1 << LED2PIN);
}

void ledGreenOff( void )
{
	LED2ONBOARDPORT |= (1 << LED2ONBOARDPIN);
	LED2PORT &= ~(1 << LED2PIN);
}

void ledGreenToggle( void )
{
	LED2ONBOARDPORT ^= (1 << LED2ONBOARDPIN);
	LED2PORT ^= (1 << LED2PIN);
}


// eof
