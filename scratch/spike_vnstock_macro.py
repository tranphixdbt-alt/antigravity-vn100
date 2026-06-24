#!/usr/bin/env python3

def check_vnstock_macro():
    try:
        from vnstock import macro_indicators, general_rating
        print("Checking vnstock macro capabilities...")
        df = macro_indicators('EXCHANGE_RATE')
        print(df.head())
    except ImportError:
        print("vnstock macro_indicators not available directly. Let's check vnstock.api or other namespaces.")
        try:
            import vnstock
            print(dir(vnstock))
        except Exception as e:
            print("Error inspecting vnstock:", e)
    except Exception as e:
        print("Error calling macro_indicators:", e)

if __name__ == "__main__":
    check_vnstock_macro()
