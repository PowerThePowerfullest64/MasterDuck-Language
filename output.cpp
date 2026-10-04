#include <iostream>

bool do_something(){
	std::cout << "Hello, wide world!" << "\n";
	return true;
}
int main(){
	if (do_something ( ) && 4 * 5 > 4){
		// pass
		std::cout << "Does it work?" << "\n";
	}
	std::cout << 1 + 2 << "\n";
	return 0;
}
