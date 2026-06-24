import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from valuation.ingest.scrapers.consensus_collector import import_vnstock_recommendations

def import_dgc():
    print("Importing VCI consensus for DGC...")
    import_vnstock_recommendations("DGC")
    print("Consensus import completed!")

if __name__ == "__main__":
    import_dgc()
