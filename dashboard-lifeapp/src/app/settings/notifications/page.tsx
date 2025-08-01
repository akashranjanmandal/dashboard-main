"use client";
import "@tabler/core/dist/css/tabler.min.css";
import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import React from "react";
import { Inter } from "next/font/google";
const inter = Inter({ subsets: ["latin"] });
import { Sidebar } from "@/components/ui/sidebar";
import {
  IconSearch,
  IconBell,
  IconSettings,
  IconDownload,
  IconX,
  IconSend,
  IconUser,
} from "@tabler/icons-react";
import { ChevronDown } from "lucide-react";

// Define the User interface based on your provided data example
interface User {
  id: number;
  school_id: number | null;
  name: string;
  guardian_name: string | null;
  email: string | null;
  username: string | null;
  mobile_no: string | null;
  type: number | null; // 3 for student?
  dob: string | null;
  gender: string | null;
  grade: string | null;
  city: string | null;
  state: string | null;
  address: string | null;
  password: string | null;
  pin: string | null;
  earn_coins: number;
  heart_coins: number;
  brain_coins: number;
  profile_image: string | null;
  image_path: string | null;
  otp: string | null;
  remember_token: string | null;
  created_at: string;
  updated_at: string;
  device: string | null;
  device_token: string | null;
  la_board_id: number | null;
  la_section_id: number | null;
  la_grade_id: number | null;
  created_by: number | null;
  school_code: string | null;
  user_rank: number | null;
  board_name: string | null;
  // Add school name if it's included in the API response
  school_name?: string;
}

// Define the response structure from the backend
interface PaginatedUsersResponse {
  users: User[];
  total_count: number; // Total matching records
  current_page: number;
  total_pages: number;
  items_per_page: number;
}

// const api_startpoint = "http://localhost:5000";
const api_startpoint = "http://152.42.239.141:5000";

function SearchableDropdown({
  options,
  placeholder,
  value,
  onChange,
  isLoading = false,
  maxDisplayItems = 100,
}: {
  options: string[];
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  isLoading?: boolean;
  maxDisplayItems?: number;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState("");
  const [displayedItems, setDisplayedItems] = useState(maxDisplayItems);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    searchTimeoutRef.current = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
      setDisplayedItems(maxDisplayItems);
    }, 300);
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [searchTerm, maxDisplayItems]);

  const filteredOptions = useMemo(() => {
    if (!debouncedSearchTerm.trim()) {
      return options;
    }
    const searchLower = debouncedSearchTerm.toLowerCase();
    return options.filter(
      (option) =>
        typeof option === "string" && option.toLowerCase().includes(searchLower)
    );
  }, [options, debouncedSearchTerm]);

  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } =
      scrollContainerRef.current;
    const scrollPosition = scrollTop + clientHeight;
    if (
      scrollHeight - scrollPosition < 50 &&
      displayedItems < filteredOptions.length
    ) {
      setDisplayedItems((prev) =>
        Math.min(prev + maxDisplayItems, filteredOptions.length)
      );
    }
  }, [displayedItems, filteredOptions.length, maxDisplayItems]);

  useEffect(() => {
    const scrollContainer = scrollContainerRef.current;
    if (scrollContainer) {
      scrollContainer.addEventListener("scroll", handleScroll);
    }
    return () => {
      if (scrollContainer) {
        scrollContainer.removeEventListener("scroll", handleScroll);
      }
    };
  }, [handleScroll]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
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

  const visibleOptions = useMemo(() => {
    return filteredOptions.slice(0, displayedItems);
  }, [filteredOptions, displayedItems]);

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
          {isLoading ? "Loading..." : value || placeholder}
        </span>
        <ChevronDown className="h-4 w-4 text-gray-500" />
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
          <div className="max-h-48 overflow-auto" ref={scrollContainerRef}>
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
                  <div className="px-3 py-2 text-gray-500">
                    No results found
                  </div>
                )}
                {hasMoreItems && (
                  <div className="flex items-center justify-center px-3 py-2 text-gray-500 border-t border-gray-100 bg-gray-50">
                    <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-purple-500"></div>
                    <span>
                      Loading more... ({visibleOptions.length} of{" "}
                      {filteredOptions.length})
                    </span>
                  </div>
                )}
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

export default function NotificationPage() {
  const [isClient, setIsClient] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [states, setStates] = useState<string[]>([]);
  const [isStatesLoading, setIsStatesLoading] = useState(false);
  const [selectedState, setSelectedState] = useState("");
  const [cities, setCities] = useState<string[]>([]);
  const [isCitiesLoading, setIsCitiesLoading] = useState(false);
  const [selectedCity, setSelectedCity] = useState("");
  const [schools, setSchools] = useState<string[]>([]); // Stores school names
  const [isSchoolsLoading, setIsSchoolsLoading] = useState(false);
  const [selectedSchool, setSelectedSchool] = useState(""); // Stores selected school name
  const [grades] = useState<string[]>(
    Array.from({ length: 12 }, (_, i) => (i + 1).toString())
  );
  const [selectedGrade, setSelectedGrade] = useState("");
  const [userTypes] = useState<string[]>(["All Users", "Student", "Teacher"]);
  const [selectedUserType, setSelectedUserType] = useState("All Users");
  const [specificUserId, setSpecificUserId] = useState("");
  const [schoolCodeInput, setSchoolCodeInput] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [selectedUserIds, setSelectedUserIds] = useState<Set<number>>(
    new Set()
  );
  const [selectAll, setSelectAll] = useState(false); // Select all on current page
  const [selectAllMatching, setSelectAllMatching] = useState(false); // New state for global select
  const [totalCount, setTotalCount] = useState(0); // Total matching records

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [notificationTitle, setNotificationTitle] = useState("");
  const [notificationMessage, setNotificationMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [modalCurrentPage, setModalCurrentPage] = useState(1);
  const modalItemsPerPage = 5;

  // --- Fetch States (No changes) ---
  useEffect(() => {
    async function fetchStates() {
      const cachedStates = sessionStorage.getItem("notification_stateList");
      if (cachedStates) {
        try {
          const parsed = JSON.parse(cachedStates);
          if (Array.isArray(parsed)) {
            setStates(parsed.filter((s) => s)); // Filter out falsy values like empty strings or null
            return;
          }
        } catch (err) {
          console.error("Error parsing cached states:", err);
        }
      }
      setIsStatesLoading(true);
      try {
        const res = await fetch(
          `${api_startpoint}/api/notification_state_list_schools`
        );
        const data = await res.json();
        if (Array.isArray(data)) {
          const stateList = data.filter((state) => state); // Filter out falsy values
          setStates(stateList);
          sessionStorage.setItem(
            "notification_stateList",
            JSON.stringify(stateList)
          );
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

  // --- Fetch Cities based on State ---
  const fetchCities = async (state: string) => {
    setIsCitiesLoading(true);
    try {
      const res = await fetch(
        `${api_startpoint}/api/notification_city_list_schools`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ state: state }),
        }
      );
      if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
      const data = await res.json();
      // Ensure data is an array and filter out falsy values
      const cityList = Array.isArray(data) ? data.filter((city) => city) : [];
      setCities(cityList);
    } catch (error) {
      console.error("❌ Error fetching city list:", error);
      setCities([]);
    } finally {
      setIsCitiesLoading(false);
    }
  };

  // Effect to fetch cities when state changes
  useEffect(() => {
    setSelectedCity(""); // Reset city selection
    setSelectedSchool(""); // Reset school selection
    setSchools([]); // Clear school list
    if (selectedState) {
      fetchCities(selectedState);
    } else {
      fetchCities(""); // Fetch all cities if no state selected
    }
  }, [selectedState]);

  // --- Fetch Schools based on State and City ---
  const fetchSchools = async (state: string, city: string) => {
    setIsSchoolsLoading(true);
    try {
      const res = await fetch(
        `${api_startpoint}/api/notification_school_list_by_location`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ state: state, city: city }),
        }
      );
      if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
      const data = await res.json();
      // Ensure data is an array and process school names
      if (Array.isArray(data)) {
        // Filter out non-string values and empty strings, then trim
        const processedSchools = data
          .filter((item: any) => typeof item === "string" && item.trim() !== "")
          .map((item: string) => item.trim());
        setSchools(processedSchools);
      } else {
        setSchools([]);
      }
    } catch (error) {
      console.error("Error fetching School list by location:", error);
      setSchools([]);
    } finally {
      setIsSchoolsLoading(false);
    }
  };

  // Effect to fetch schools when state or city changes
  useEffect(() => {
    setSelectedSchool(""); // Reset school selection when location filters change
    if (selectedState || selectedCity) {
      // Fetch if either state or city is selected
      fetchSchools(selectedState, selectedCity);
    } else {
      // Optionally, fetch all schools if no filters
      // fetchSchools("", "");
      setSchools([]); // Or clear list
    }
  }, [selectedState, selectedCity]); // Depend on both state and city

  useEffect(() => {
    setIsClient(true);
    // Initial fetch - Corrected number of arguments
    fetchUsers("", "", "", "", "", "All Users", "", "", 1, itemsPerPage); // Pass page 1
  }, []);

  // --- Updated fetchUsers to handle pagination and total count ---
  const fetchUsers = async (
    query: string,
    state: string,
    city: string,
    school: string, // This is now school name
    grade: string,
    userType: string,
    specificUserId: string,
    schoolCode: string,
    page: number, // Add page parameter
    perPage: number // Add perPage parameter
  ) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${api_startpoint}/api/notification_users_search_paginated`, // Updated endpoint
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            search: query,
            state: state,
            city: city,
            school_name: school, // Send school name
            grade: grade,
            user_type: userType,
            specific_user_id: specificUserId,
            school_code: schoolCode,
            page: page, // Send page
            items_per_page: perPage, // Send items per page
          }),
        }
      );
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Network response was not ok: ${errorText}`);
      }
      const paginatedData: PaginatedUsersResponse = await response.json();

      setUsers(paginatedData.users);
      setTotalCount(paginatedData.total_count);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error occurred";
      console.error("Fetch Users Error:", error);
      setError(errorMessage);
      setUsers([]);
      setTotalCount(0); // Reset total count on error
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setCurrentPage(1);
    // Reset selections when filters/search changes
    setSelectedUserIds(new Set());
    setSelectAll(false);
    setSelectAllMatching(false);
    fetchUsers(
      searchTerm,
      selectedState,
      selectedCity,
      selectedSchool,
      selectedGrade,
      selectedUserType,
      specificUserId,
      schoolCodeInput,
      1, // Start from page 1
      itemsPerPage
    );
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const handleClearFilters = () => {
    setSearchTerm("");
    setSelectedState("");
    setSelectedCity("");
    setSelectedSchool("");
    setSelectedGrade("");
    setSelectedUserType("All Users");
    setSpecificUserId("");
    setSchoolCodeInput("");
    setCurrentPage(1);
    // Reset selections when filters/search changes
    setSelectedUserIds(new Set());
    setSelectAll(false);
    setSelectAllMatching(false);
    fetchUsers("", "", "", "", "", "All Users", "", "", 1, itemsPerPage);
  };

  // --- Handle Page Change ---
  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    fetchUsers(
      searchTerm,
      selectedState,
      selectedCity,
      selectedSchool,
      selectedGrade,
      selectedUserType,
      specificUserId,
      schoolCodeInput,
      newPage,
      itemsPerPage
    );
    // DO NOT reset selectedUserIds on page change
  };

  const handleCheckboxChange = (userId: number) => {
    setSelectedUserIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(userId)) {
        newSet.delete(userId);
      } else {
        newSet.add(userId);
      }
      // Update selectAll based on whether all displayed items are selected
      const allDisplayedIds = currentItems.map((u) => u.id);
      const allSelected =
        allDisplayedIds.length > 0 &&
        allDisplayedIds.every((id) => newSet.has(id));
      setSelectAll(allSelected);

      // If deselecting one, global select is definitely false
      if (newSet.has(userId)) {
        setSelectAllMatching(false);
      }
      return newSet;
    });
  };

  // --- Handle Select All on Current Page ---
  const handleSelectAllChange = () => {
    if (selectAll) {
      // Deselect all currently displayed items
      setSelectedUserIds((prev) => {
        const newSet = new Set(prev);
        currentItems.forEach((item) => newSet.delete(item.id));
        return newSet;
      });
    } else {
      // Select all currently displayed items
      setSelectedUserIds((prev) => {
        const newSet = new Set(prev);
        currentItems.forEach((item) => newSet.add(item.id));
        return newSet;
      });
    }
    setSelectAll(!selectAll);
    // Deselecting global select if user interacts with page select
    setSelectAllMatching(false);
  };

  // --- Handle Select All Matching Records (New Functionality) ---
  const handleSelectAllMatchingChange = async () => {
    if (selectAllMatching) {
      // Deselect all - clear the set
      setSelectedUserIds(new Set());
      setSelectAll(false); // Also deselect page select
    } else {
      // Select all matching - This requires a backend call to get IDs
      try {
        // Call a new endpoint to get all matching user IDs
        const response = await fetch(
          `${api_startpoint}/api/notification_users_search_ids`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              search: searchTerm,
              state: selectedState,
              city: selectedCity,
              school_name: selectedSchool,
              grade: selectedGrade,
              user_type: selectedUserType,
              specific_user_id: specificUserId,
              school_code: schoolCodeInput,
              // No pagination needed for IDs
            }),
          }
        );
        if (!response.ok) throw new Error("Failed to fetch user IDs");
        const userIds: number[] = await response.json(); // Expect array of IDs
        setSelectedUserIds(new Set(userIds));
        setSelectAll(false); // Deselect page select
      } catch (err) {
        console.error("Error fetching all matching user IDs:", err);
        alert(
          "Could not select all users. Please try again or select manually."
        );
        return;
      }
    }
    setSelectAllMatching(!selectAllMatching);
  };

  const openNotificationModal = () => {
    if (selectedUserIds.size === 0) {
      alert("Please select at least one user.");
      return;
    }
    setIsModalOpen(true);
    setSendError(null);
    setModalCurrentPage(1); // Reset modal pagination
  };

  const closeNotificationModal = () => {
    setIsModalOpen(false);
    setNotificationTitle("");
    setNotificationMessage("");
    setSendError(null);
  };

  const handleSendNotification = async () => {
    if (!notificationTitle.trim() || !notificationMessage.trim()) {
      setSendError("Please enter both title and message.");
      return;
    }

    setIsSending(true);
    setSendError(null);
    try {
      const userIdsArray = Array.from(selectedUserIds);
      const response = await fetch(`${api_startpoint}/api/notification_send`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_ids: userIdsArray,
          title: notificationTitle,
          message: notificationMessage,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.message ||
            `Failed to send notification: ${response.status} ${response.statusText}`
        );
      }

      const result = await response.json();
      console.log("Notification sent successfully:", result);
      alert("Notification sent successfully!");
      closeNotificationModal();
      setSelectedUserIds(new Set()); // Clear selections
      setSelectAll(false);
      setSelectAllMatching(false);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "An unknown error occurred while sending the notification.";
      console.error("Send Notification Error:", error);
      setSendError(errorMessage);
    } finally {
      setIsSending(false);
    }
  };

  // --- Pagination calculations ---
  const totalPages = Math.ceil(totalCount / itemsPerPage);
  const currentItems = users; // Users are now paginated from backend

  // --- Modal Pagination (No changes) ---
  const modalSelectedUsers = Array.from(selectedUserIds)
    .map((id) => users.find((u) => u.id === id) || { id, name: `User ${id}` })
    .filter((u) => u) as User[]; // Fallback name if not in current page
  const modalIndexOfLastItem = modalCurrentPage * modalItemsPerPage;
  const modalIndexOfFirstItem = modalIndexOfLastItem - modalItemsPerPage;
  const modalCurrentItems = modalSelectedUsers.slice(
    modalIndexOfFirstItem,
    modalIndexOfLastItem
  );
  const modalTotalPages = Math.ceil(
    modalSelectedUsers.length / modalItemsPerPage
  );

  const PaginationControls = ({
    currentPage,
    totalPages,
    setCurrentPage,
    itemsPerPage,
    totalItems,
  }: {
    currentPage: number;
    totalPages: number;
    setCurrentPage: (page: number) => void;
    itemsPerPage: number;
    totalItems: number;
  }) => (
    <div className="d-flex justify-content-between align-items-center mt-3">
      <div className="text-muted">
        Showing {Math.min((currentPage - 1) * itemsPerPage + 1, totalItems)} to{" "}
        {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems}{" "}
        entries
      </div>
      <div className="d-flex gap-2 align-items-center">
        <select
          className="form-select form-select-sm"
          value={itemsPerPage}
          onChange={(e) => {
            const newItemsPerPage = Number(e.target.value);
            setItemsPerPage(newItemsPerPage);
            setCurrentPage(1); // Reset to first page when changing items per page
            fetchUsers(
              searchTerm,
              selectedState,
              selectedCity,
              selectedSchool,
              selectedGrade,
              selectedUserType,
              specificUserId,
              schoolCodeInput,
              1, // Page 1
              newItemsPerPage
            );
          }}
        >
          {[10, 25, 50, 100].map((size) => (
            <option key={size} value={size}>
              {size} per page
            </option>
          ))}
        </select>
        <button
          className="btn btn-outline-secondary"
          onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
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
          onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
          disabled={currentPage >= totalPages}
        >
          Next
        </button>
      </div>
    </div>
  );

  // --- Crucial useEffect to update selectAll state ---
  // This useEffect correctly determines if ALL items on the CURRENT page are selected
  // based on the persistent selectedUserIds set.
  useEffect(() => {
    if (currentItems.length === 0) {
      setSelectAll(false);
      return;
    }
    // Check if every item on the current page is in the selectedUserIds set
    const allItemsOnPageSelected = currentItems.every((item) =>
      selectedUserIds.has(item.id)
    );
    setSelectAll(allItemsOnPageSelected);
  }, [currentItems, selectedUserIds]); // Dependencies are crucial

  if (!isClient) {
    return (
      <div className={`page bg-light ${inter.className} font-sans`}>
        <Sidebar />
        <div className="page-wrapper" style={{ marginLeft: "250px" }}>
          <header className="navbar navbar-expand-md navbar-light bg-white shadow-sm border-bottom mb-3">
            <div className="container-fluid">
              <div className="d-flex align-items-center w-full">
                <span className="font-bold text-xl text-black">
                  LifeAppDashboard
                </span>
              </div>
            </div>
          </header>
          <div className="container-xl pt-0 pb-4">
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Send Notifications</h3>
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

  return (
    <div className={`page bg-light ${inter.className} font-sans`}>
      <Sidebar />
      <div className="page-wrapper" style={{ marginLeft: "250px" }}>
        <div className="page-body">
          <div className="container-xl pt-0 pb-4">
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Send Notifications</h3>
              </div>
              <div className="card-body">
                <div className="d-flex mb-3 gap-3 flex-wrap">
                  {/* --- Updated User Type Filter - Simple Dropdown --- */}
                  <div className="col-12 col-md-6 col-lg-3">
                    <select
                      className="form-select"
                      value={selectedUserType}
                      onChange={(e) => setSelectedUserType(e.target.value)}
                    >
                      <option value="All Users">All Users</option>
                      <option value="Student">Student</option>
                      <option value="Teacher">Teacher</option>
                    </select>
                  </div>
                  {/* --- End of User Type Filter Replacement --- */}

                  {/* Specific User ID Filter */}
                  <div className="col-12 col-md-6 col-lg-3">
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Enter Specific User ID"
                      value={specificUserId}
                      onChange={(e) => setSpecificUserId(e.target.value)}
                    />
                  </div>
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
                      options={schools} // Ensure this is an array of strings
                      placeholder="Select School"
                      value={selectedSchool}
                      onChange={(val) => setSelectedSchool(val)}
                      isLoading={isSchoolsLoading}
                      maxDisplayItems={200}
                    />
                  </div>
                  {/* School Code Filter */}
                  <div className="col-12 col-md-6 col-lg-3">
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Enter School Code"
                      value={schoolCodeInput}
                      onChange={(e) => setSchoolCodeInput(e.target.value)}
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
                  <div className="d-flex gap-3">
                    <button
                      className="btn btn-primary rounded-sm"
                      onClick={handleSearch}
                    >
                      <IconSearch size={18} className="me-1" /> Search
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={handleClearFilters}
                    >
                      <IconX size={18} className="me-1" /> Clear
                    </button>
                  </div>
                </div>

                {/* --- Updated Send Notification Button Position and Logic --- */}
                {totalCount > 0 && (
                  <div className="d-flex justify-content-between align-items-center mb-2">
                    <div>
                      {/* Optional: Show count of selected users */}
                      {selectedUserIds.size > 0 && (
                        <span className="text-muted small">
                          {selectedUserIds.size} user(s) selected.
                          {selectAllMatching &&
                            ` (${totalCount} matching users selected)`}
                        </span>
                      )}
                    </div>
                    <div>
                      {/* Select All Matching Checkbox */}
                      <div className="form-check form-check-inline">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id="selectAllMatchingCheckbox"
                          checked={selectAllMatching}
                          onChange={handleSelectAllMatchingChange}
                        />
                        <label
                          className="form-check-label"
                          htmlFor="selectAllMatchingCheckbox"
                        >
                          Select All Matching ({totalCount})
                        </label>
                      </div>
                      {/* Send Notification Button */}
                      {selectedUserIds.size > 0 && (
                        <button
                          className="btn btn-success ms-2" // Added margin start for spacing
                          onClick={openNotificationModal}
                        >
                          <IconSend size={18} className="me-1" /> Send
                          Notification
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {loading ? (
                  <div className="text-center py-4">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                  </div>
                ) : error ? (
                  <div className="alert alert-danger" role="alert">
                    Error loading users: {error}
                  </div>
                ) : (
                  <div className="table-responsive">
                    <table className="table table-vcenter table-hover">
                      <thead>
                        <tr>
                          <th style={{ width: "1%" }}>
                            <input
                              className="form-check-input m-0 align-middle"
                              type="checkbox"
                              aria-label="Select all on this page"
                              checked={selectAll} // Correctly reflects page selection state
                              onChange={handleSelectAllChange}
                            />
                          </th>
                          <th>ID</th>
                          <th>Name</th>
                          <th>Username</th>
                          <th>Mobile</th>
                          <th>Type</th>
                          <th>Grade</th>
                          <th>School</th>
                          <th>School Code</th>
                          <th>City</th>
                          <th>State</th>
                        </tr>
                      </thead>
                      <tbody>
                        {currentItems.length === 0 ? (
                          <tr>
                            <td colSpan={11} className="text-center">
                              No users found
                            </td>
                          </tr>
                        ) : (
                          currentItems.map((user) => (
                            <tr key={user.id}>
                              <td>
                                <input
                                  className="form-check-input m-0 align-middle"
                                  type="checkbox"
                                  aria-label={`Select user ${user.name}`}
                                  checked={selectedUserIds.has(user.id)} // Correctly reflects global selection state
                                  onChange={() => handleCheckboxChange(user.id)}
                                />
                              </td>
                              <td>{user.id}</td>
                              <td>{user.name}</td>
                              <td>{user.username || "-"}</td>
                              <td>{user.mobile_no || "-"}</td>
                              <td>
                                {user.type === 3
                                  ? "Student"
                                  : user.type === 2
                                  ? "Teacher"
                                  : "Other"}
                              </td>
                              <td>{user.grade || "-"}</td>
                              <td>
                                {user.school_name || user.school_id || "-"}
                              </td>
                              <td>{user.school_code || "-"}</td>
                              <td>{user.city || "-"}</td>
                              <td>{user.state || "-"}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                    {!loading && !error && totalCount > 0 && (
                      <PaginationControls
                        currentPage={currentPage}
                        totalPages={totalPages}
                        setCurrentPage={handlePageChange} // Use the new handler
                        itemsPerPage={itemsPerPage}
                        totalItems={totalCount} // Use total count
                      />
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Notification Modal  */}
      {isModalOpen && (
        <div
          className="modal fade show"
          style={{ display: "block" }}
          tabIndex={-1}
          aria-labelledby="notificationModalLabel"
          aria-hidden="true"
        >
          <div className="modal-dialog modal-lg">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title" id="notificationModalLabel">
                  Confirm Notification
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={closeNotificationModal}
                  aria-label="Close"
                ></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label htmlFor="notificationTitle" className="form-label">
                    Title
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="notificationTitle"
                    value={notificationTitle}
                    onChange={(e) => setNotificationTitle(e.target.value)}
                    placeholder="Enter notification title"
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="notificationMessage" className="form-label">
                    Message
                  </label>
                  <textarea
                    className="form-control"
                    id="notificationMessage"
                    rows={5}
                    value={notificationMessage}
                    onChange={(e) => setNotificationMessage(e.target.value)}
                    placeholder="Enter notification message"
                  ></textarea>
                </div>

                <div className="mb-3">
                  <h6>Selected Users ({selectedUserIds.size}):</h6>
                  <div className="table-responsive">
                    <table className="table table-bordered table-sm">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Name</th>
                        </tr>
                      </thead>
                      <tbody>
                        {modalCurrentItems.length === 0 ? (
                          <tr>
                            <td colSpan={2} className="text-center">
                              No users selected
                            </td>
                          </tr>
                        ) : (
                          modalCurrentItems.map((user) => (
                            <tr key={user.id}>
                              <td>{user.id}</td>
                              <td>{user.name}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                    {modalSelectedUsers.length > modalItemsPerPage && (
                      <PaginationControls
                        currentPage={modalCurrentPage}
                        totalPages={modalTotalPages}
                        setCurrentPage={setModalCurrentPage}
                        itemsPerPage={modalItemsPerPage}
                        totalItems={modalSelectedUsers.length}
                      />
                    )}
                  </div>
                </div>

                {sendError && (
                  <div className="alert alert-danger" role="alert">
                    {sendError}
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={closeNotificationModal}
                  disabled={isSending}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleSendNotification}
                  disabled={isSending}
                >
                  {isSending ? (
                    <>
                      <span
                        className="spinner-border spinner-border-sm me-1"
                        role="status"
                        aria-hidden="true"
                      ></span>
                      Sending...
                    </>
                  ) : (
                    <>
                      <IconSend size={18} className="me-1" /> Send Notification
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {isModalOpen && <div className="modal-backdrop fade show"></div>}
    </div>
  );
}
