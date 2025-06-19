'use client'
import '@tabler/core/dist/css/tabler.min.css';
// import 'bootstrap/dist/css/bootstrap.min.css';
import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import React from 'react';
import { Inter } from 'next/font/google';
const inter = Inter({ subsets: ['latin'] });
import { Sidebar } from '@/components/ui/sidebar';
import { IconSearch, IconBell, IconSettings, IconDownload, IconX } from '@tabler/icons-react';
import { ChevronDown } from 'lucide-react';


// Define TypeScript interface for coupon data
interface CouponRedemption {
    'Student Name': string;
    'School Name': string;
    'Mobile Number': string;
    state: string;
    city: string;
    grade: string | number;
    'Coupon Title': string;
    'Coins Redeemed': number;
    user_id: number;
    'Coupon Redeemed Date': string;
}

// const api_startpoint = 'https://lifeapp-api-vv1.vercel.app'
const api_startpoint = 'http://152.42.239.141:5000'
// const api_startpoint = 'http://152.42.239.141:5000'


interface SearchableDropdownProps {
    options: string[];
    placeholder: string;
    value: string;
    onChange: (value: string) => void;
    isLoading?: boolean;
    maxDisplayItems?: number;
}

function SearchableDropdown({
    options,
    placeholder,
    value,
    onChange,
    isLoading = false,
    maxDisplayItems = 100
}: SearchableDropdownProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");
    const [debouncedSearchTerm, setDebouncedSearchTerm] = useState("");
    const [displayedItems, setDisplayedItems] = useState(maxDisplayItems);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    
    // Implement debounce for search
    useEffect(() => {
        if (searchTimeoutRef.current) {
            clearTimeout(searchTimeoutRef.current);
        }
        
        searchTimeoutRef.current = setTimeout(() => {
            setDebouncedSearchTerm(searchTerm);
            // Reset displayed items when search changes
            setDisplayedItems(maxDisplayItems);
        }, 300);
        
        return () => {
            if (searchTimeoutRef.current) {
                clearTimeout(searchTimeoutRef.current);
            }
        };
    }, [searchTerm, maxDisplayItems]);

    // Get filtered options based on search term
    const filteredOptions = useMemo(() => {
        if (!debouncedSearchTerm.trim()) {
            return options;
        }
        
        const searchLower = debouncedSearchTerm.toLowerCase();
        
        return options.filter(option => 
            typeof option === "string" && 
            option.toLowerCase().includes(searchLower)
        );
    }, [options, debouncedSearchTerm]);

    // Handle scroll event to implement infinite scrolling
    const handleScroll = useCallback(() => {
        if (!scrollContainerRef.current) return;
        
        const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
        const scrollPosition = scrollTop + clientHeight;
        
        // If user has scrolled to near bottom, load more items
        if (scrollHeight - scrollPosition < 50 && displayedItems < filteredOptions.length) {
            setDisplayedItems(prev => Math.min(prev + maxDisplayItems, filteredOptions.length));
        }
    }, [displayedItems, filteredOptions.length, maxDisplayItems]);

    // Add scroll event listener
    useEffect(() => {
        const scrollContainer = scrollContainerRef.current;
        if (scrollContainer) {
            scrollContainer.addEventListener('scroll', handleScroll);
        }
        
        return () => {
            if (scrollContainer) {
                scrollContainer.removeEventListener('scroll', handleScroll);
            }
        };
    }, [handleScroll]);

    // Handle clicks outside the dropdown
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        
        if (isOpen) {
            document.addEventListener("mousedown", handleClickOutside);
        }
        
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [isOpen]);

    const handleSelect = (option: string) => {
        onChange(option);
        setIsOpen(false);
        setSearchTerm("");
        setDebouncedSearchTerm("");
        setDisplayedItems(maxDisplayItems);
    };

    // The options to display - limited by displayedItems count
    const visibleOptions = useMemo(() => {
        return filteredOptions.slice(0, displayedItems);
    }, [filteredOptions, displayedItems]);

    // Calculate if there are more items to load
    const hasMoreItems = filteredOptions.length > displayedItems;
    return (
        <div className="relative" ref={dropdownRef}>
            <div
                className="flex w-full cursor-pointer items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                onClick={() => setIsOpen(!isOpen)}
                role="combobox"
                aria-expanded={isOpen}
                aria-haspopup="listbox"
            >
                <span className={value ? "text-gray-900" : "text-gray-500"}>
                    {isLoading ? "Loading..." : (value || placeholder)}
                </span>
                <ChevronDown className="h-4 w-4 text-gray-500"/>
            </div>

            {isOpen && (
                <div className="absolute z-10 mt-1 w-full rounded-md border border-gray-200 bg-white shadow-lg">
                    <div className="p-2">
                        <input
                            type="text"
                            className="w-full rounded-md border border-gray-300 px-3 py-1 text-sm focus:border-purple-500 focus:outline-none"
                            placeholder="Search..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                            autoFocus
                        />
                    </div>
                    <div 
                        className="max-h-48 overflow-auto"
                        ref={scrollContainerRef}
                    >
                        {isLoading ? (
                            <div className="px-3 py-2 text-gray-500">Loading options...</div>
                        ) : (
                            <>
                                {visibleOptions.length > 0 ? (
                                    visibleOptions.map((option, index) => (
                                        <div
                                            key={index}
                                            className="cursor-pointer px-3 py-2 text-gray-900 hover:bg-purple-50"
                                            onClick={() => handleSelect(option)}
                                        >
                                            {option}
                                        </div>
                                    ))
                                ) : (
                                    <div className="px-3 py-2 text-gray-500">No results found</div>
                                )}
                                
                                {/* Show loading more indicator */}
                                {hasMoreItems && (
                                    <div className="flex items-center justify-center px-3 py-2 text-gray-500 border-t border-gray-100 bg-gray-50">
                                        <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-purple-500"></div>
                                        <span>Loading more... ({visibleOptions.length} of {filteredOptions.length})</span>
                                    </div>
                                )}
                                
                                {/* Show total count if filtered */}
                                {debouncedSearchTerm && filteredOptions.length > 0 && (
                                    <div className="px-3 py-2 text-xs text-center text-gray-500 bg-gray-50 border-t border-gray-100">
                                        Found {filteredOptions.length} matching results
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default function CouponsRedeemed() {
    const [isClient, setIsClient] = useState(false);
    const [coupons, setCoupons] = useState<CouponRedemption[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState<string>('');

    // Add filter-related state here
    const [states, setStates] = useState<string[]>([]);
    const [isStatesLoading, setIsStatesLoading] = useState(false);
    const [selectedState, setSelectedState] = useState("");
    const [cities, setCities] = useState<string[]>([]);
    const [isCitiesLoading, setIsCitiesLoading] = useState(false);
    const [selectedCity, setSelectedCity] = useState("");
    const [schools, setSchools] = useState<string[]>([]);
    const [isSchoolsLoading, setIsSchoolsLoading] = useState(false);
    const [selectedSchools, setSelectedSchools] = useState("");

    useEffect(() => {
        async function fetchStates() {
            // Check cache first
            const cachedStates = sessionStorage.getItem("stateList");
            if (cachedStates) {
                setStates(JSON.parse(cachedStates));
                return;
            }

            setIsStatesLoading(true);
            try {
                const res = await fetch(`${api_startpoint}/api/state_list_teachers`);
                const data: { state: string }[] = await res.json();

                if (Array.isArray(data)) {
                    const stateList = data
                        .map((item) => (item.state ? item.state.trim() : ""))
                        .filter((state) => state !== ""); // Filter out empty states

                    setStates(stateList);
                    // Cache the results
                    sessionStorage.setItem("stateList", JSON.stringify(stateList));
                } else {
                    console.error("Unexpected API response format:", data);
                    setStates([]);
                }
            } catch (error) {
                console.error("Error fetching state list:", error);
                setStates([]);
            } finally {
                setIsStatesLoading(false);
            }
        }

        fetchStates();
    }, []);

    const fetchCities = async (state: string) => {
        if (!state) return;
    
        console.log("Fetching cities for state:", state);
    
        setIsCitiesLoading(true);
        try {
            const res = await fetch(`${api_startpoint}/api/city_list_teachers`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: state })
            });
    
            if (!res.ok) {
                throw new Error(`HTTP error! Status: ${res.status}`);
            }
    
            const data = await res.json();
    
            console.log("Raw API Response:", data); // ✅ Check if cities are being received
    
            if (Array.isArray(data) && data.length > 0) {
                const cityList: string[] = data.map(city => 
                    typeof city === 'string' ? city.trim() : city.city ? city.city.trim() : ''
                ).filter(city => city !== "");
    
                setCities(cityList);
                sessionStorage.setItem(`cityList_${state}`, JSON.stringify(cityList));
    
                console.log(`✅ Loaded ${cityList.length} cities for ${state}`);
            } else {
                console.warn("⚠ No cities found for state:", state);
                setCities([]); // Clear cities if none found
            }
        } catch (error) {
            console.error("❌ Error fetching city list:", error);
            setCities([]);
        } finally {
            setIsCitiesLoading(false);
        }
    };

    useEffect(() => {
        if (selectedState) {
            setCities([]);
            setSelectedCity("");
            fetchCities(selectedState);
        } else {
            setCities([]);
            setSelectedCity("");
        }
    }, [selectedState]);

    useEffect(() => {
        async function fetchSchools() {
            // Check cache first
            const cachedSchools = sessionStorage.getItem('SchoolList');
            if (cachedSchools) {
                try {
                    const parsed = JSON.parse(cachedSchools);
                    if (Array.isArray(parsed) && parsed.length > 0) {
                        setSchools(parsed);
                        return;
                    }
                } catch (err) {
                    console.error("Error parsing cached schools:", err);
                    // Continue to fetch if cache parse fails
                }
            }
            
            setIsSchoolsLoading(true);
            try {
                const res = await fetch(`${api_startpoint}/api/school_list`);
                const data: { name: string }[] = await res.json();
                
                if (Array.isArray(data)) {
                    // Create a reference to collect all processed schools
                    let allProcessedSchools: string[] = [];
                    
                    // Process data in chunks to avoid UI freezing with large datasets
                    const processSchoolsBatch = (startIndex: number, batchSize: number): void => {
                        const endIndex = Math.min(startIndex + batchSize, data.length);
                        const batch = data
                            .slice(startIndex, endIndex)
                            .map(item => item.name ? item.name.trim() : "")
                            .filter(name => name !== "");
                        
                        // Add to our complete collection
                        allProcessedSchools = [...allProcessedSchools, ...batch];
                        
                        // Update the state with what we've processed so far
                        setSchools(allProcessedSchools);
                        
                        if (endIndex < data.length) {
                            // Process next batch in the next tick to avoid blocking the UI
                            setTimeout(() => processSchoolsBatch(endIndex, batchSize), 0);
                        } else {
                            // All done, cache the results using our complete reference
                            sessionStorage.setItem('SchoolList', JSON.stringify(allProcessedSchools));
                            setIsSchoolsLoading(false);
                        }
                    };
                    
                    // Start processing in batches (100 items at a time)
                    processSchoolsBatch(0, 100);
                } else {
                    console.error("Unexpected API response format:", data);
                    setSchools([]);
                    setIsSchoolsLoading(false);
                }
            } catch (error) {
                console.error("Error fetching School list:", error);
                setSchools([]);
                setIsSchoolsLoading(false);
            }
        }
        
        fetchSchools();
    }, []);

    // Set isClient to true after component mounts
    useEffect(() => {
        setIsClient(true);
        fetchCoupons('', '', '', '', '', '', '', '', '');
    }, []);

    // Add to existing state declarations
    const [selectedGrade, setSelectedGrade] = useState("");
    // Add near the top of the component
    const grades = Array.from({length: 12}, (_, i) => (i + 1).toString());

    const [couponTitles, setCouponTitles] = useState<string[]>([]);
    const [isCouponTitlesLoading, setIsCouponTitlesLoading] = useState(false);
    const [selectedCouponTitle, setSelectedCouponTitle] = useState("");

    useEffect(() => {
        async function fetchCouponTitles() {
            const cachedTitles = sessionStorage.getItem("couponTitles");
            if (cachedTitles) {
                setCouponTitles(JSON.parse(cachedTitles));
                return;
            }
    
            setIsCouponTitlesLoading(true);
            try {
                const response = await fetch(`${api_startpoint}/api/coupon_titles`);
                if (!response.ok) throw new Error('Failed to fetch coupon titles');
                const titles = await response.json();
                setCouponTitles(titles);
                sessionStorage.setItem("couponTitles", JSON.stringify(titles));
            } catch (error) {
                console.error("Error fetching coupon titles:", error);
            } finally {
                setIsCouponTitlesLoading(false);
            }
        }
        fetchCouponTitles();
    }, []);

    const [searchMobile, setSearchMobile] = useState('');
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");

    // Add these state variables at the top of your component
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(10);

    // Calculate pagination indexes
    const indexOfLastItem = currentPage * itemsPerPage;
    const indexOfFirstItem = indexOfLastItem - itemsPerPage;
    const currentItems = coupons.slice(indexOfFirstItem, indexOfLastItem);
    const totalPages = Math.ceil(coupons.length / itemsPerPage);
    // Function to fetch coupons from the backend with an optional search term
    const fetchCoupons = async (
        query: string,
        state: string,
        mobile: string,
        city: string,
        school: string,
        grade: string,
        couponTitle: string,
        startDate: string,
        endDate: string
    ) => {
        setLoading(true);
        try {
            const response = await fetch(`${api_startpoint}/api/coupon_redeem_search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    search: query,
                    mobile: mobile,
                    state: state,
                    city: city,
                    school: school,
                    grade: grade,
                    coupon_title: couponTitle,
                    start_date: startDate,
                    end_date: endDate
                }),
            });
            
            if (!response.ok) throw new Error('Network response was not ok');
            const tableData = await response.json();
            setCoupons(tableData as CouponRedemption[]);
            setError(null);
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };
    // When the search button is clicked, fetch coupons based on the search term.
    const handleSearch = () => {
        setCurrentPage(1);
        fetchCoupons(
            searchTerm,
            selectedState,
            searchMobile,
            selectedCity, 
            selectedSchools,
            selectedGrade,
            selectedCouponTitle,
            startDate,
            endDate
        );
    };
    

    // Handle search input change
    const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearchTerm(e.target.value);
    };

    const handleClearFilters = () => {
        setSearchTerm('');
        setSelectedState('');
        setSelectedCity('');
        setSelectedSchools('');
        setSelectedGrade(''); // Add grade reset
        setSelectedCouponTitle('');
        setSearchMobile('');
        setStartDate("");
        setEndDate("");
        fetchCoupons('', '', '', '', '', '', '', '', '');
    };
    
    // Export to CSV
    const exportToCSV = () => {
        const headers = ['Student Name', 'School Name', 'Mobile Number', 'State', 'City', 'Grade', 'Coins Redeemed', 'User ID', 'Coupon Redeemed Date'];
        const csvRows = [headers.join(',')];
        coupons.forEach(coupon => {
            const row = [
                coupon['Student Name'] || '',
                coupon['School Name'] || '',
                coupon['Mobile Number'] || '',
                coupon.state || '',
                coupon.city || '',
                coupon.grade || '',
                coupon['Coupon Title'] || '',
                coupon['Coins Redeemed'] || '',
                coupon.user_id,
                coupon['Coupon Redeemed Date'] || ''
            ];
            csvRows.push(row.join(','));
        });
        const csvContent = csvRows.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'coupon_redemptions.csv';
        link.click();
    };

    // Format date function
    const formatDate = (dateString: string): string => {
        if (!dateString) return '';
        try {
            const date = new Date(dateString);
            return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
        } catch (e) {
            return '';
        }
    };

    if (!isClient) {
        return (
            <div className={`page bg-light ${inter.className} font-sans`}>
                <Sidebar />
                <div className="page-wrapper" style={{ marginLeft: '250px' }}>
                    <header className="navbar navbar-expand-md navbar-light bg-white shadow-sm border-bottom mb-3">
                        <div className="container-fluid">
                            <div className="d-flex align-items-center w-full">
                                <span className='font-bold text-xl text-black'>LifeAppDashboard</span>
                            </div>
                        </div>
                    </header>
                    <div className='container-xl pt-0 pb-4'>
                        <div className="card">
                            <div className="card-header">
                                <h3 className="card-title">Coupon Redemptions</h3>
                            </div>
                            <div className="card-body">
                                <div className="text-center py-4">
                                    <div className="spinner-border text-primary" role="status">
                                        <span className="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }



    function PaginationControls() {
        return (
            <div className="d-flex justify-content-between align-items-center mt-3">
                <div className="text-muted">
                    Showing {indexOfFirstItem + 1} to {Math.min(indexOfLastItem, coupons.length)} of {coupons.length} entries
                </div>
                
                <div className="d-flex gap-2 align-items-center">
                    <select
                        className="form-select form-select-sm"
                        value={itemsPerPage}
                        onChange={(e) => {
                            setItemsPerPage(Number(e.target.value));
                            setCurrentPage(1); // Reset to first page when changing page size
                        }}
                    >
                        {[10, 25, 50, 100].map(size => (
                            <option key={size} value={size}>{size} per page</option>
                        ))}
                    </select>
    
                    <button
                        className="btn btn-outline-secondary"
                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        disabled={currentPage === 1}
                    >
                        Previous
                    </button>
                    <div className="w-1/3 p-0">
                        <span className="p-0 d-flex">
                            Page {currentPage} of {totalPages}
                        </span>
                    </div>   
                    
    
                    <button
                        className="btn btn-outline-secondary"
                        onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                        disabled={currentPage >= totalPages}
                    >
                        Next
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className={`page bg-light ${inter.className} font-sans`}>
            <Sidebar />
            <div className="page-wrapper" style={{ marginLeft: '250px' }}>
                {/* <header className="navbar navbar-expand-md navbar-light bg-white shadow-sm border-bottom mb-3">
                    <div className="container-fluid">
                        <div className="d-flex align-items-center w-full">
                            <span className='font-bold text-xl text-black'>LifeAppDashboard</span>
                            <div className='w-5/6 h-10'></div>
                            <div className="d-flex gap-3 align-items-center">
                                <a href="#" className="btn btn-light btn-icon">
                                    <IconSearch size={20} className="text-muted"/>
                                </a>
                                <a href="#" className="btn btn-light btn-icon position-relative">
                                    <IconBell size={20} className="text-muted"/>
                                    <span className="badge bg-danger position-absolute top-0 end-0">3</span>
                                </a>
                                <a href="#" className="btn btn-light btn-icon">
                                    <IconSettings size={20} className="text-muted"/>
                                </a>
                            </div>
                        </div>
                    </div>
                </header> */}
                <div className='page-body'>
                    <div className='container-xl pt-0 pb-4'>
                        <div className="card">
                            <div className="card-header">
                                <h3 className="card-title">Coupon Redemptions</h3>
                            </div>
                            <div className="card-body">
                                <div className="d-flex mb-3 gap-3 flex-wrap">
                                    
                                    
                                    {/* State Filter */}
                                    <div className="col-12 col-md-6 col-lg-3">
                                        <SearchableDropdown
                                            options={states}
                                            placeholder="Select State"
                                            value={selectedState}
                                            onChange={(val) => setSelectedState(val)}
                                            isLoading={isStatesLoading}
                                            maxDisplayItems={200}
                                        />
                                    </div>

                                    {/* City Filter */}
                                    <div className="col-12 col-md-6 col-lg-3">
                                        <SearchableDropdown
                                            options={cities}
                                            placeholder="Select City"
                                            value={selectedCity}
                                            onChange={(val) => setSelectedCity(val)}
                                            isLoading={isCitiesLoading}
                                            maxDisplayItems={200}
                                        />
                                    </div>

                                    {/* School Filter */}
                                    <div className="col-12 col-md-6 col-lg-3">
                                        <SearchableDropdown
                                            options={schools}
                                            placeholder="Select School"
                                            value={selectedSchools}
                                            onChange={(val) => setSelectedSchools(val)}
                                            isLoading={isSchoolsLoading}
                                            maxDisplayItems={200}
                                        />
                                    </div>
                                    <div className="col-12 col-md-6 col-lg-3">
                                        <div className="input-group gap-3 h-full">
                                            <input 
                                                type="text" 
                                                className="form-control" 
                                                placeholder="Search User Name" 
                                                value={searchTerm}
                                                onChange={handleSearchChange}
                                            />
                                            
                                        </div>
                                    </div>
                                    <div className="col-12 col-md-6 col-lg-3">
                                        <SearchableDropdown
                                            options={grades}
                                            placeholder="Select Grade"
                                            value={selectedGrade}
                                            onChange={(val) => setSelectedGrade(val)}
                                            maxDisplayItems={12}
                                        />
                                    </div>
                                    {/* Coupon Title Filter */}
                                    <div className="col-12 col-md-6 col-lg-3">
                                        <SearchableDropdown
                                            options={couponTitles}
                                            placeholder="Select Coupon Title"
                                            value={selectedCouponTitle}
                                            onChange={(val) => setSelectedCouponTitle(val)}
                                            isLoading={isCouponTitlesLoading}
                                            maxDisplayItems={200}
                                        />
                                    </div>
                                    <div className="col-12 col-md-6 col-lg-3">
                                        <div className="input-group gap-3 h-full">
                                            <input 
                                                type="text" 
                                                className="form-control" 
                                                placeholder="Search Mobile No..."
                                                value={searchMobile}
                                                onChange={(e) => {
                                                    const sanitized = e.target.value.replace(/[^0-9]/g, '');
                                                    setSearchMobile(sanitized);
                                                }} // Allow only numbers
                                                pattern="[0-9]*"
                                                maxLength={10}
                                            />
                                        </div>
                                    </div>
                                    <div className="col-12 col-md-6 col-lg-3">
                                        <input
                                            type="date"
                                            className="form-control"
                                            value={startDate}
                                            onChange={(e) => setStartDate(e.target.value)}
                                            max={endDate || undefined}
                                        />
                                    </div>
                                    <div className="col-12 col-md-6 col-lg-3">
                                        <input
                                            type="date"
                                            className="form-control"
                                            value={endDate}
                                            onChange={(e) => setEndDate(e.target.value)}
                                            min={startDate || undefined}
                                        />
                                    </div>
                                    <div className="d-flex gap-3">
                                        <button className="btn btn-primary rounded-sm" onClick={handleSearch}>
                                            <IconSearch size={18} className="me-1" /> Search
                                        </button>
                                        <button 
                                            className="btn btn-secondary" 
                                            onClick={handleClearFilters}
                                            disabled={!searchTerm && !selectedState && !selectedCity && !selectedSchools && !selectedGrade && !selectedCouponTitle && !searchMobile && !startDate && !endDate}
                                        >
                                            <IconX size={18} className="me-1" /> Clear
                                        </button>
                                        <button className="btn btn-primary" onClick={exportToCSV}>
                                            <IconDownload size={18} className="me-1" /> Export
                                        </button>
                                    </div>
                                    
                                </div>

                                {loading ? (
                                    <div className="text-center py-4">
                                        <div className="spinner-border text-primary" role="status">
                                            <span className="visually-hidden">Loading...</span>
                                        </div>
                                    </div>
                                ) : error ? (
                                    <div className="alert alert-danger" role="alert">
                                        Error loading data: {error}
                                    </div>
                                ) : (
                                    <div className="table-responsive">
                                        <table className="table table-vcenter table-hover">
                                            <thead>
                                                <tr>
                                                    <th>Student Name</th>
                                                    <th>School Name</th>
                                                    <th>Mobile Number</th>
                                                    <th>State</th>
                                                    <th>City</th>
                                                    <th>Grade</th>
                                                    <th>Coupon Title</th>
                                                    <th>Coins Redeemed</th>
                                                    <th>User ID</th>
                                                    <th>Redeemed Date</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {currentItems.length === 0 ? (
                                                    <tr>
                                                        <td colSpan={9} className="text-center">No redemptions found</td>
                                                    </tr>
                                                ) : (
                                                    currentItems.map((coupon, index) => (
                                                        <tr key={index}>
                                                            <td>{coupon['Student Name']}</td>
                                                            <td>{coupon['School Name']}</td>
                                                            <td>{coupon['Mobile Number']}</td>
                                                            <td>{coupon.state}</td>
                                                            <td>{coupon.city}</td>
                                                            <td>{coupon.grade}</td>
                                                            <td>{coupon['Coupon Title']}</td>
                                                            <td>{coupon['Coins Redeemed']}</td>
                                                            <td>{coupon.user_id}</td>
                                                            <td>{formatDate(coupon['Coupon Redeemed Date'])}</td>
                                                        </tr>
                                                    ))
                                                )}
                                            </tbody>
                                        </table>
                                        
                                        {!loading && !error && coupons.length > 0 && (
                                            <PaginationControls />
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
