#include <iostream>
#include <array>

int fib(int n) {
	if (n <= 0) {
		return 0;
	}
	if (n == 1) {
		return 1;
	}
	return fib ( n - 1 ) + fib ( n - 2 );
}
int main() {
	std::array<int, 43> fibs;
	for (int i = 0; i < fibs . size ( ); i++) {
		fibs [ i ] = fib ( i );
	}
	for (auto n : fibs) {
		std::cout << n << "\n";
	}
	return 0;
}
