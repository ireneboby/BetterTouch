//
//  main.m
//  bettertouch4mac
//
//  Created by Ella Smith on 2024-10-09.
//

#import <Foundation/Foundation.h>
#import <CoreBluetooth/CoreBluetooth.h>
#import <ApplicationServices/ApplicationServices.h>
//#import <ORSSerial/ORSSerialPort.h>
//#import <ORSSerial/ORSSerialPortManager.h>

#define CUSTOM_SERVICE_UUID @"00001234-0000-1000-8000-00805f9b34fb"
#define CUSTOM_CHAR_UUID @"00005678-0000-1000-8000-00805f9b34fb"

#define COM_PORT @"/dev/cu.usbmodem14201"
#define BAUD_RATE 9600
#define TIMEOUT 0.1

#define N 8
#define M 8

#define WINDOW_SIZE 10

#define X_MIN 25
#define X_MAX 1050
#define Y_MIN 145
#define Y_MAX 700

@interface ScreenState : NSObject
- (ScreenState *)onEvent:(int)event;
- (NSArray *)dataParsing:(int)data;
- (CGPoint)coordinateDetermination:(NSArray *)xBitArray yBitArray:(NSArray *)yBitArray;
@end

@interface UntouchedState : ScreenState
@end

@interface SingleTouchState : ScreenState
@property (nonatomic) CGPoint prevCoord;
- (instancetype)initWithStartX:(int)startX startY:(int)startY;
@end

@implementation ScreenState
- (ScreenState *)onEvent:(int)event {
    [NSException raise:@"NotImplementedException" format:@"This method should be overridden"];
    return nil;
}
- (NSArray *)dataParsing:(int)data {
    NSMutableArray *yBitArray = [NSMutableArray array];
    NSMutableArray *xBitArray = [NSMutableArray array];
    
    for (int i = N-1; i >= 0; i--) {
        [yBitArray addObject:@((data >> i) & 1)];
    }
    
    for (int i = N+M-1; i >= N; i--) {
        [xBitArray addObject:@((data >> i) & 1)];
    }
    
    if (![xBitArray containsObject:@1] && ![yBitArray containsObject:@1]) {
        return nil;
    }
    
    return @[xBitArray, yBitArray];
}

- (CGPoint)coordinateDetermination:(NSArray *)xBitArray yBitArray:(NSArray *)yBitArray {
    int xIndex = 0, xIndexCount = 0;
    for (int i = 0; i < xBitArray.count; i++) {
        if ([xBitArray[i] boolValue]) {
            xIndexCount++;
            xIndex += i;
        }
    }
    if (xIndexCount == 0) return CGPointZero;
    int xCoord = round((xIndex / (float)xIndexCount / N) * (X_MAX - X_MIN) + X_MIN);
    
    int yIndex = 0, yIndexCount = 0;
    for (int i = 0; i < yBitArray.count; i++) {
        if ([yBitArray[i] boolValue]) {
            yIndexCount++;
            yIndex += i;
        }
    }
    int yCoord = round((yIndex / (float)yIndexCount / M) * (Y_MAX - Y_MIN) + Y_MIN);
    
    return CGPointMake(xCoord, yCoord);
}

@end

@implementation UntouchedState
- (ScreenState *)onEvent:(int)event {
    NSArray *bitArrays = [self dataParsing:event];
    if (!bitArrays) return nil;

    CGPoint coord = [self coordinateDetermination:bitArrays[0] yBitArray:bitArrays[1]];
    if (CGPointEqualToPoint(coord, CGPointZero)) return nil;

    CGEventRef mouseDown = CGEventCreateMouseEvent(NULL, kCGEventLeftMouseDown, coord, kCGMouseButtonLeft);
    CGEventPost(kCGHIDEventTap, mouseDown);
    CFRelease(mouseDown);

    return [[SingleTouchState alloc] initWithStartX:coord.x startY:coord.y];
}
@end

@implementation SingleTouchState
- (instancetype)initWithStartX:(int)startX startY:(int)startY {
    self = [super init];
    if (self) {
        _prevCoord = CGPointMake(startX, startY);
    }
    return self;
}

- (ScreenState *)onEvent:(int)event {
    NSArray *bitArrays = [self dataParsing:event];
    if (!bitArrays) return nil;

    CGPoint coord = [self coordinateDetermination:bitArrays[0] yBitArray:bitArrays[1]];
    if (CGPointEqualToPoint(coord, CGPointZero)) {
        CGEventRef mouseUp = CGEventCreateMouseEvent(NULL, kCGEventLeftMouseUp, _prevCoord, kCGMouseButtonLeft);
        CGEventPost(kCGHIDEventTap, mouseUp);
        CFRelease(mouseUp);
        return [[UntouchedState alloc] init];
    }

    if (!CGPointEqualToPoint(coord, _prevCoord)) {
        CGEventRef move = CGEventCreateMouseEvent(NULL, kCGEventMouseMoved, coord, kCGMouseButtonLeft);
        CGEventPost(kCGHIDEventTap, move);
        CFRelease(move);
        _prevCoord = coord;
    }

    return nil;
}
@end

ScreenState *currState;
NSMutableArray *window;

void testScreenControl() {
    ScreenState *currState = [[UntouchedState alloc] init];
    
    // Simulate a touch event with hardcoded data
    int testEvent = 0b0000001100000011; // Example data, adjust as needed
    
    ScreenState *nextState = [currState onEvent:testEvent];
    if (nextState) {
        currState = nextState;
    }
    
    // Simulate another touch event
    testEvent = 0b0000011000000110; // Example data, adjust as needed
    
    nextState = [currState onEvent:testEvent];
    if (nextState) {
        currState = nextState;
    }
    
    // Simulate touch release
    testEvent = 0b0000000000000000; // Example data, adjust as needed
    
    nextState = [currState onEvent:testEvent];
    if (nextState) {
        currState = nextState;
    }
}
//void mainSerial() {
//    ORSSerialPort *port = [ORSSerialPort serialPortWithPath:COM_PORT];
//    port.baudRate = @(BAUD_RATE);
//    port.delegate = (id<ORSSerialPortDelegate>)self;
//    [port open];
//
//    currState = [[UntouchedState alloc] init];
//    window = [NSMutableArray array];
//
//    while (YES) {
//        NSData *data = [port readDataToLength:1 timeout:TIMEOUT];
//        if (!data) continue;
//
//        int event = *(int *)[data bytes];
//        ScreenState *nextState = [currState onEvent:event];
//        if (nextState) {
//            currState = nextState;
//        }
//    }
//}

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        testScreenControl();
    }
    return 0;
}
