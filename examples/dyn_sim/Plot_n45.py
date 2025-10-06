import sys
#sys.path.append('/Users/noralillelien/Documents/TOPS_low_inertia/')
sys.path.append('/Users/theathormodsen/Library/Mobile Documents/com~apple~CloudDocs/Masteroppgave/Kode og simulering/TOPS_low_inertia_Thea/')
import inertia_sim.utility_functions_NJ as uf
# /Users/theathormodsen/Library/Mobile Documents/com~apple~CloudDocs/Masteroppgave/Kode og simulering/TOPS_low_inertia_Thea/
if __name__ == '__main__':  
    #folder_path = '/Users/noralillelien/Documents/TOPS_low_inertia/Results'
    folder_path = '/Users/theathormodsen/Library/Mobile Documents/com~apple~CloudDocs/Masteroppgave/Kode og simulering/TOPS_low_inertia_Thea/Results'
    results,file_names = uf.format_results(folder_path)
    uf.plot_freq(results, file_names)
