
#include <iostream>
#include <vector>
#include <string>

#include <chrono>
#include <windows.h>

using namespace std;

int main()
{

    auto start = std::chrono::high_resolution_clock::now();
    
    Sleep(500);

    auto stop = std::chrono::high_resolution_clock::now();

    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(stop - start);

    cout << duration.count() << endl; 
}