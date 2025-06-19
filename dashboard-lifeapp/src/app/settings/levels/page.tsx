'use client'
import { useState, useEffect } from 'react';
import React from 'react';
import { Inter } from 'next/font/google';
const inter = Inter({ subsets: ['latin'] });
import { Sidebar } from '@/components/ui/sidebar';
import { cn } from "@/lib/utils";
import '@tabler/core/dist/css/tabler.min.css';
import { IconEdit, IconTrash } from '@tabler/icons-react';

interface Levels {
    created_at: string,
    description: string,
    id: number,
    jigyasa_points: number,
    mission_points: number,
    pragya_points: number,
    puzzle_points: number,
    puzzle_time: number,
    quiz_points: number,
    quiz_time: number,
    riddle_points: number,
    riddle_time: number,
    status: number,
    title: string,
    updated_at: string
}

// const api_startpoint = 'https://lifeapp-api-vv1.vercel.app'
const api_startpoint = 'http://152.42.239.141:5000'
// const api_startpoint = 'http://152.42.239.141:5000'
export default function SettingsLevels() {
    const [levels, setLevels] = useState<Levels[]>([]);
    const [loading, setLoading] = useState(true);
    const [isAddLoading, setIsAddLoading] = useState(false)
    const [isEditLoading, setIsEditLoading] = useState(false)
    async function fetchLevels() {
        try {
            setLoading(true); // Start loading
            const response = await fetch(`${api_startpoint}/api/levels`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ page: 1 }) // Adjust pagination if needed
            });
            const data: Levels[] = await response.json();
            setLevels(data);
            setLoading(false); // Stop loading
        } catch (error) {
            console.error('Error fetching levels:', error);
            setLoading(false); // Stop loading
        }
    };
    
    useEffect(() => {
        fetchLevels();
    }, []);


    const [showAddModal, setShowAddModal] = useState(false);
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [status, setStatus] = useState(0);
    const [jigyasaPoints, setJigyasaPoints] = useState(0);
    const [missionPoints, setMissionPoints] = useState(0);
    const [pragyaPoints, setPragyaPoints] = useState(0);
    const [puzzlePoints, setPuzzlePoints] = useState(0);
    const [puzzleTime, setPuzzleTime] = useState(0);
    const [quizPoints, setQuizPoints] = useState(0);
    const [quizTime, setQuizTime] = useState(0);
    const [riddlePoints, setRiddlePoints] = useState(0);
    const [riddleTime, setRiddleTime] = useState(0);

    const handleSubmit = async (e: { preventDefault: () => void; }) => {
        e.preventDefault();
        setIsAddLoading(true)
        const newLevel = {
            title: { en: title },
            description: { en: description },
            jigyasa_points: jigyasaPoints,
            mission_points: missionPoints,
            pragya_points: pragyaPoints,
            puzzle_points: puzzlePoints,
            puzzle_time: puzzleTime,
            quiz_time: quizTime,
            quiz_points: quizPoints,
            riddle_points: riddlePoints,
            riddle_time: riddleTime,
            status: status,
            
        };
    
        try {
            const response = await fetch(`${api_startpoint}/api/levels_new`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newLevel)
            });
    
            if (response.ok) {
                setShowAddModal(false);
                fetchLevels(); // Refresh table
            }
        } catch (error) {
            console.error('Error adding level:', error);
        } finally {
            setIsAddLoading(false)
        }
    };
    
    // First, add a state for the edit modal and form values
    const [showEditModal, setShowEditModal] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string>('');
    const [selectedLevel, setSelectedLevel] = useState<Levels | null>(null);
    const [editFormValues, setEditFormValues] = useState<Levels>({
    id: 0,
    title: "",
    description: "",
    jigyasa_points: 0,
    mission_points: 0,
    pragya_points: 0,
    puzzle_points: 0,
    puzzle_time: 60,
    quiz_points: 0,
    quiz_time: 60,
    riddle_points: 0,
    riddle_time: 60,
    status: 1,
    created_at: "",
    updated_at: ""
    });

    // Add a handler for editing a level
    const handleEditClick = (level: Levels) => {
        setSelectedLevel(level);
      
        try {
          const parsedTitle       = JSON.parse(level.title);
          const parsedDescription = JSON.parse(level.description);
      
          setEditFormValues({
            ...editFormValues,
            id: level.id,
            // now display the human string, not the JSON blob:
            title: parsedTitle.en,
            description: parsedDescription.en,
            jigyasa_points: level.jigyasa_points,
            mission_points: level.mission_points,
            pragya_points: level.pragya_points,
            puzzle_points: level.puzzle_points,
            puzzle_time: level.puzzle_time,
            quiz_points: level.quiz_points,
            quiz_time: level.quiz_time,
            riddle_points: level.riddle_points,
            riddle_time: level.riddle_time,
            status: level.status,
            created_at: level.created_at,
            updated_at: level.updated_at
          });
        } catch (err) {
          console.error("JSON parse error:", err);
          setErrorMessage("Failed to parse level data");
        }
      
        setShowEditModal(true);
    };

    // Handle form field changes in the edit modal
    const handleEditChange = (e: { target: { name: any; value: any; }; }) => {
    const { name, value } = e.target;
    // Convert numeric fields to numbers
    const numericFields = [
        'jigyasa_points', 'mission_points', 'pragya_points',
        'puzzle_points', 'puzzle_time', 'quiz_points',
        'quiz_time', 'riddle_points', 'riddle_time', 'status'
    ];
    
    setEditFormValues({
        ...editFormValues,
        [name]: numericFields.includes(name) ? Number(value) : value
    });
    };

    // Handle edit form submission
    const handleEditSubmit = async (e: { preventDefault: () => void; }) => {
        e.preventDefault();
        setIsEditLoading(true)
        try {
            // Convert text values back to JSON objects for API
            const formDataForAPI = {
                id: editFormValues.id,
                title: { en: editFormValues.title },
                description: { en: editFormValues.description },
                jigyasa_points: editFormValues.jigyasa_points,
                mission_points: editFormValues.mission_points,
                pragya_points: editFormValues.pragya_points,
                puzzle_points: editFormValues.puzzle_points,
                puzzle_time: editFormValues.puzzle_time,
                quiz_points: editFormValues.quiz_points,
                quiz_time: editFormValues.quiz_time,
                riddle_points: editFormValues.riddle_points,
                riddle_time: editFormValues.riddle_time,
                status: editFormValues.status,
            };
            
            const res = await fetch(`${api_startpoint}/api/levels_update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formDataForAPI)
            });

            if (res.ok) {
                setShowEditModal(false);
                setSelectedLevel(null);
                setErrorMessage('');
                // Reset form and refresh data
                setEditFormValues({
                    id: 0, title: "", description: "",
                    jigyasa_points: 0, mission_points: 0, pragya_points: 0,
                    puzzle_points: 0, puzzle_time: 60, quiz_points: 0,
                    quiz_time: 60, riddle_points: 0, riddle_time: 60, status: 1,
                    created_at: "", updated_at:''
                });
                await fetchLevels();
            } else {
                const errorData = await res.json();
                setErrorMessage(errorData.error || 'Error updating level');
            }
        } catch (err) {
            setErrorMessage('Error connecting to API');
            console.error('Error updating level:', err);
        } finally {
            setIsEditLoading(true)
        }
    };





    const handleDelete = async (id: number) => {
        if (!window.confirm('Are you sure you want to delete this level?')) {
            return;
        }
    
        try {
            const response = await fetch(`${api_startpoint}/api/levels_delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id })
            });
    
            if (response.ok) {
                alert('Level deleted successfully!');
                fetchLevels(); // Refresh the table
            } else {
                alert('Failed to delete level.');
            }
        } catch (error) {
            console.error('Error deleting level:', error);
        }
    };
    

    return (
        <div className={`page bg-body ${inter.className} font-sans`}>
            <Sidebar />

            {/* Main Content */}
            <div className="page-wrapper" style={{ marginLeft: '250px' }}>
                <div className='page-body'>
                    <div className='container-xl pt-4 pb-4 space-y-2'>
                        <div className="card shadow-sm border-0 ">
                            <div className="card-body overflow-x-scroll">
                                <h4 className="card-title ">Levels</h4>

                                {/* Levels Table */}
                                <div className="table-responsive">
                                    {loading ? (
                                        <div className="flex justify-center items-center h-40">
                                            <div className="animate-spin rounded-full h-10 w-10 border-t-4 border-blue-800"></div>
                                        </div>
                                        ) : (
                                        <table className="table table-striped">
                                            <thead>
                                                <tr>
                                                    <th>ID</th>
                                                    <th>Title</th>
                                                    <th>Description</th>
                                                    <th>Status</th> 
                                                    <th>Mission Points</th>
                                                    <th>Jigyasa Points</th>
                                                    <th>Pragya Points</th>
                                                    <th>Quiz Points</th>
                                                    <th>Riddle Points</th>
                                                    <th>Puzzle Points</th>
                                                    <th>Quiz Time</th>
                                                    <th>Riddle Time</th>
                                                    <th>Puzzle Time</th>
                                                    <th>Created At</th>
                                                    <th>Updated At</th>
                                                    <th>Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {levels.map((level) => (
                                                    <tr key={level.id}>
                                                        <td>{level.id}</td>
                                                        <td>{JSON.parse(level.title).en}</td>
                                                        <td>{JSON.parse(level.description).en}</td>
                                                        <td>{level.status == 1? 'Active': "Inactive"}</td>
                                                        <td>{level.mission_points}</td>
                                                        <td>{level.jigyasa_points}</td>
                                                        <td>{level.pragya_points}</td>
                                                        <td>{level.quiz_points}</td>
                                                        <td>{level.riddle_points}</td>
                                                        <td>{level.puzzle_points}</td>
                                                        <td>{level.quiz_time}</td>
                                                        <td>{level.riddle_time}</td>
                                                        <td>{level.puzzle_time}</td>
                                                        <td>{new Date(level.created_at).toLocaleString()}</td>
                                                        <td>{new Date(level.updated_at).toLocaleString()}</td>
                                                        <td className='text-center'>
                                                            <button className="btn btn-sm btn-outline-primary mx-1" 
                                                                onClick={() => handleEditClick(level)}>
                                                                <IconEdit size={16} />
                                                            </button>
                                                            <button className="btn btn-sm btn-outline-danger"
                                                                onClick={() => handleDelete(level.id)}
                                                            >
                                                                <IconTrash size={16} />
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    )}
                                </div>

                            </div>
                            

                        </div>
                        <div className="w-1/6 h-6">
                            <button 
                                    className="btn btn-primary mb-3"
                                    onClick={() => setShowAddModal(true)}
                                >
                                    Add New Level
                            </button>
                        </div>
                        {/* Sliding Add Modal */}
                        {showAddModal && (
                            <div className="modal fade show d-block mt-0" 
                                style={{ 
                                    background: 'rgba(0,0,0,0.5)', 
                                    position: 'fixed', 
                                    top: 0, left: 0, 
                                    width: '100vw', height: '100vh', 
                                    zIndex: 1050 
                                }} 
                                tabIndex={-1} role="dialog"
                                >
                                <div className="modal-dialog modal-lg modal-dialog-end">
                                    <div className="modal-content"
                                        style={{ background: 'white', borderRadius: '8px', boxShadow: '0px 4px 10px rgba(0,0,0,0.2)' }}
                                        >
                                        <div className="modal-header"
                                            style={{ background: '#f8f9fa', borderBottom: '1px solid #dee2e6' }}
                                            >
                                            <h5 className="modal-title">Add New Level</h5>
                                            <button type="button" className="btn-close" onClick={() => setShowAddModal(false)}></button>
                                        </div>
                                        <div className="modal-body">
                                            <form onSubmit={handleSubmit}>
                                                <div className="mb-3">
                                                    <label className="form-label">Title</label>
                                                    <input type="text" className="form-control" value={title} onChange={(e) => setTitle(e.target.value)} required />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="form-label">Description</label>
                                                    <input type="text" className="form-control" value={description} onChange={(e) => setDescription(e.target.value)} required />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="form-label">Status</label>
                                                    <select
                                                        name="status"
                                                        value={status}
                                                        onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                                                        setStatus(Number(e.target.value))
                                                        }
                                                        className="w-full border p-2"
                                                        required
                                                    >
                                                        <option value="">Select status</option>
                                                        <option value="1">Active</option>
                                                        <option value="0">Inactive</option>
                                                    </select>
                                                </div>

                                                <div className="mb-3">
                                                    <label className="form-label">Mission Points</label>
                                                    <input type="number" className="form-control" value={missionPoints} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setMissionPoints(Number(e.target.value))} required />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="form-label">Jigyasa Points</label>
                                                    <input type="number" className="form-control" value={jigyasaPoints} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setJigyasaPoints(Number(e.target.value))} required />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="form-label">Pragya Points</label>
                                                    <input type="number" className="form-control" value={pragyaPoints} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setPragyaPoints(Number(e.target.value))} required />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="form-label">Quiz Points</label>
                                                    <input type="number" className="form-control" value={quizPoints} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setQuizPoints(Number(e.target.value))} required />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="form-label">Puzzle Points</label>
                                                    <input type="number" className="form-control" value={puzzlePoints} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setPuzzlePoints(Number(e.target.value))} required />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="form-label">Riddle Points</label>
                                                    <input type="number" className="form-control" value={riddlePoints} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setRiddlePoints(Number(e.target.value))} required />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="form-label">Quiz Time</label>
                                                    <input type="number" className="form-control" value={quizTime} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setQuizTime(Number(e.target.value))} required />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="form-label">Puzzle Time</label>
                                                    <input type="number" className="form-control" value={puzzleTime} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setPuzzleTime(Number(e.target.value))} required />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="form-label">Riddle Time</label>
                                                    <input type="number" className="form-control" value={riddleTime} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setRiddleTime(Number(e.target.value))} required />
                                                </div>
                                                <button type="submit" className="btn btn-success" disabled={isAddLoading}>
                                                    {isAddLoading && <div className='animate-spin rounded-full border-t-4 border-white w-4 h-4 mr-2'></div>}
                                                    {isAddLoading? 'Saving':'Save Level'}</button>
                                            </form>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                        {/* Edit Modal */}
                        {showEditModal && (
                            <div className="fixed top-0 right-0 h-full w-2/5 shadow-lg z-50 transform transition-transform duration-300 overflow-y-auto mt-0 bg-white"
                            style={{ transform: showEditModal ? 'translateX(0)' : 'translateX(100%)' }}>
                            <div className="p-4 border-b flex justify-between items-center">
                                <h2 className="text-xl font-semibold">Edit Level</h2>
                                <button onClick={() => {
                                    setShowEditModal(false);
                                    setSelectedLevel(null);
                                }}>
                                    <svg xmlns="http://www.w3.org/2000/svg" className="icon icon-tabler icon-tabler-x" width="24" height="24" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round">
                                        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                                        <path d="M18 6L6 18"></path>
                                        <path d="M6 6l12 12"></path>
                                    </svg>
                                </button>
                            </div>
                            <div className="p-4">
                                {errorMessage && <p className="text-red-500">{errorMessage}</p>}    
                                <form onSubmit={handleEditSubmit}>
                                    <div className="mb-4">
                                        <label className="block mb-1">Title</label>
                                        <input
                                            type="text"
                                            name="title"
                                            value={editFormValues.title}
                                            onChange={handleEditChange}
                                            className="w-full border p-2"
                                            required
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label className="block mb-1">Description</label>
                                        <input
                                            type="text"
                                            name="description"
                                            value={editFormValues.description}
                                            onChange={handleEditChange}
                                            className="w-full border p-2"
                                            required
                                        />
                                    </div>
                                    <div className="d-flex flex-col gap-1">
                                        <div className="mb-4">
                                            <label className="block mb-1">Jigyasa Points</label>
                                            <input
                                                type="number"
                                                name="jigyasa_points"
                                                value={editFormValues.jigyasa_points}
                                                onChange={handleEditChange}
                                                className="w-full border p-2"
                                                required
                                            />
                                        </div>
                                        <div className="mb-4">
                                            <label className="block mb-1">Mission Points</label>
                                            <input
                                                type="number"
                                                name="mission_points"
                                                value={editFormValues.mission_points}
                                                onChange={handleEditChange}
                                                className="w-full border p-2"
                                                required
                                            />
                                        </div>
                                        <div className="mb-4">
                                            <label className="block mb-1">Pragya Points</label>
                                            <input
                                                type="number"
                                                name="pragya_points"
                                                value={editFormValues.pragya_points}
                                                onChange={handleEditChange}
                                                className="w-full border p-2"
                                                required
                                            />
                                        </div>
                                        <div className="mb-4">
                                            <label className="block mb-1">Puzzle Points</label>
                                            <input
                                                type="number"
                                                name="puzzle_points"
                                                value={editFormValues.puzzle_points}
                                                onChange={handleEditChange}
                                                className="w-full border p-2"
                                                required
                                            />
                                        </div>
                                        <div className="mb-4">
                                            <label className="block mb-1">Puzzle Time</label>
                                            <input
                                                type="number"
                                                name="puzzle_time"
                                                value={editFormValues.puzzle_time}
                                                onChange={handleEditChange}
                                                className="w-full border p-2"
                                                required
                                            />
                                        </div>
                                        <div className="mb-4">
                                            <label className="block mb-1">Quiz Points</label>
                                            <input
                                                type="number"
                                                name="quiz_points"
                                                value={editFormValues.quiz_points}
                                                onChange={handleEditChange}
                                                className="w-full border p-2"
                                                required
                                            />
                                        </div>
                                        <div className="mb-4">
                                            <label className="block mb-1">Quiz Time</label>
                                            <input
                                                type="number"
                                                name="quiz_time"
                                                value={editFormValues.quiz_time}
                                                onChange={handleEditChange}
                                                className="w-full border p-2"
                                                required
                                            />
                                        </div>
                                        <div className="mb-4">
                                            <label className="block mb-1">Riddle Points</label>
                                            <input
                                                type="number"
                                                name="riddle_points"
                                                value={editFormValues.riddle_points}
                                                onChange={handleEditChange}
                                                className="w-full border p-2"
                                                required
                                            />
                                        </div>
                                        <div className="mb-4">
                                            <label className="block mb-1">Riddle Time</label>
                                            <input
                                                type="number"
                                                name="riddle_time"
                                                value={editFormValues.riddle_time}
                                                onChange={handleEditChange}
                                                className="w-full border p-2"
                                                required
                                            />
                                        </div>
                                        <div className="mb-4">
                                            <label className="block mb-1">Status</label>
                                            <select
                                                name="status"
                                                value={editFormValues.status}
                                                onChange={handleEditChange}
                                                className="w-full border p-2"
                                                required
                                            >
                                                <option value={1}>Active</option>
                                                <option value={0}>Inactive</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div className="flex justify-end gap-2">
                                        <button 
                                            type="button" 
                                            className="btn btn-secondary" 
                                            onClick={() => {
                                            setShowEditModal(false);
                                            setSelectedLevel(null);
                                            }}
                                        >
                                            Cancel
                                        </button>
                                        <button type="submit" className="btn btn-primary" disabled={isEditLoading}>
                                            {isEditLoading && <div className= 'animate-spin rounded-full border-t-4 border-white w-4 h-4 mr-2'></div>}
                                            {isEditLoading ?'Updating':'Update Level'}
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

