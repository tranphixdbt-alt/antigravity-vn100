#!/usr/bin/env python3

def check_vnstock_market():
    from vnstock.api.market import Market
    from vnstock.api.fundamental import Fundamental
    
    m = Market(source="VCI")
    print("Market dir:", [d for d in dir(m) if not d.startswith('_')])
    
    f = Fundamental(source="VCI")
    print("Fundamental dir:", [d for d in dir(f) if not d.startswith('_')])

if __name__ == "__main__":
    check_vnstock_market()
