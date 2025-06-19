'use client'
import React, { useEffect, useState, ChangeEvent, FormEvent } from 'react';
import { Inter } from 'next/font/google';
import '@tabler/core/dist/css/tabler.min.css';
import { Sidebar } from '@/components/ui/sidebar';
import NumberFlow from '@number-flow/react';
import { IconEdit, IconPlus, IconTrash } from '@tabler/icons-react';
import Papa from 'papaparse';
const inter = Inter({ subsets: ['latin'] });
// const api_startpoint = 'https://lifeapp-api-vv1.vercel.app'
const api_startpoint = 'http://152.42.239.141:5000'

// const api_startpoint = 'http://152.42.239.141:5000'




interface ModalProps {
    mode: 'add' | 'edit';
    initial?: VisionRow;
    onClose: ()=>void;
    onSuccess: ()=>void;
}

interface QuestionPayload {
  question_id?: number;               // optional on add
  question_type: 'mcq' | 'reflection' | 'image';
  question: string;
  options?: { a: string; b: string; c: string; d: string };
  correct_answer?: string;
}

function AddEditModal({
  mode,
  initial,
  onClose,
  onSuccess
}: ModalProps) {
  const isEdit = mode === 'edit';

  const [title, setTitle] = useState(initial?.title || '');
  const [desc, setDesc]   = useState(initial?.description || '');
  const [you, setYou]     = useState(initial?.youtube_url || '');
  const [forAll, setForAll] = useState(initial ? initial.allow_for.toString() : '1');
  const [subj, setSubj]   = useState(initial?.subject_id?.toString() || '');
  const [lvl, setLvl]     = useState(initial?.level_id?.toString() || '');
  const [stat, setStat]   = useState(initial?.status.toString() || '1');
  const [mcqInputMode, setMcqInputMode] = useState<'manual' | 'csv'>('manual');
  const [questionType, setQuestionType] = useState<'mcq'|'reflection'|'image'>(initial?.questions?.[0]?.question_type || 'mcq');
  
  // question states
  const [mcqQ, setMcqQ]       = useState('');
  const [mcqOpts, setMcqOpts] = useState({ a: '', b: '', c: '', d: '' });
  const [mcqAns, setMcqAns]   = useState('');
  const [refQ, setRefQ]       = useState('');
  const [imgQ, setImgQ]       = useState('');

  // MCQ questions list
  const initialMcq = isEdit
    ? initial?.questions
        .filter(q => q.question_type === 'mcq')
        .map(q => ({ question: q.question, options: q.options ?? {a:'',b:'',c:'',d:''}, correct_answer: q.correct_answer ?? '' }))
    : [{ question: '', options: {a:'',b:'',c:'',d:''}, correct_answer: '' }];
  const [mcqList, setMcqList] = useState(initialMcq || [{ question: '', options: {a:'',b:'',c:'',d:''}, correct_answer: '' }]);

const handleCsvUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (!file) return;

  Papa.parse(file, {
    complete: (result) => {
      const parsed = result.data as string[][];
      const cleaned = parsed
        .filter(row => row.length >= 6)
        .map(row => ({
          question: row[0]?.trim(),
          options: {
            a: row[1]?.trim(),
            b: row[2]?.trim(),
            c: row[3]?.trim(),
            d: row[4]?.trim(),
          },
          correct_answer: row[5]?.trim().toLowerCase(),
        }));
      setMcqList(cleaned);
    },
    skipEmptyLines: true,
  });
};
  
  // Reflection/Image question
  const initialSingle = isEdit
    ? initial?.questions.find(q => q.question_type !== 'mcq')?.question ?? ''
    : '';
  const [singleQ, setSingleQ] = useState(initialSingle);

  // add or remove MCQ entries
  const addMcq = () => {
    if (mcqList.length < 5) {
      setMcqList([...mcqList, { question: '', options: {a:'',b:'',c:'',d:''}, correct_answer: '' }]);
    }
  };
  const removeMcq = (idx: number) => {
    setMcqList(mcqList.filter((_, i) => i !== idx));
  };

  // dropdown data
  const [subjects, setSubjects] = useState<any[]>([]);
  const [levels,   setLevels]   = useState<any[]>([]);
  const [loading,  setLoading]  = useState(false);

  // load subjects, levels and prefill when editing
  useEffect(() => {
    fetch(`${api_startpoint}/api/subjects_list`, {
      method:'POST',
      headers:{ 'Content-Type':'application/json' },
      body: JSON.stringify({ status: '1' })
    })
      .then(r => r.json())
      .then(setSubjects);

    fetch(`${api_startpoint}/api/levels`, {
      method:'POST',
      headers:{ 'Content-Type':'application/json' },
      body: JSON.stringify({ page: 1 })
    })
      .then(r => r.json())
      .then(setLevels);

    if (isEdit && initial) {
      initial.questions.forEach(q => {
        if (q.question_type === 'mcq') {
          setMcqQ(q.question);
          setMcqOpts(q.options  || { a:'',b:'',c:'',d:'' });
          setMcqAns(q.correct_answer || '');
        } else if (q.question_type === 'reflection') {
          setRefQ(q.question);
        } else if (q.question_type === 'image') {
          setImgQ(q.question);
        }
      });
    }
  }, []);

  const handleSave = async () => {
    setLoading(true);

    const questions: QuestionPayload[] = [];
    if (questionType === 'mcq') {
      mcqList.forEach(q => {
        if (q.question) {
          questions.push({ question_type: 'mcq', question: q.question, options: q.options, correct_answer: q.correct_answer });
        }
      });
    } else {
      questions.push({ question_type: questionType, question: singleQ });
    }

    if (!subj || !lvl || !title || !desc) {
      alert("Please fill in all required fields.");
      setLoading(false);
      return;
    }
    
    const payload = {
      title,
      description:  desc,
      youtube_url: you,
      allow_for:   forAll,
      subject_id:  subj,
      level_id:    lvl,
      status:      stat,
      questions
    };

    const url    = isEdit ? `${api_startpoint}/api/visions/${initial!.vision_id}` : `${api_startpoint}/api/visions`;
    const method = isEdit ? 'PUT' : 'POST';

console.log(payload)

    const res = await fetch(url, {
      method, 
      headers: { 'Content-Type':'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      onSuccess();
      onClose();
    } else {
      alert('Save failed');
    }
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 mt-0">
      <div className="bg-white p-6 rounded-lg w-full max-w-lg max-h-[90vh] overflow-auto">
        <h2 className="text-xl font-semibold mb-4">
          {isEdit ? 'Edit' : 'Add'} Vision
        </h2>

        {/* vision fields */}
        <input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Title" className="w-full border p-2 rounded mb-2" />
        <textarea value={desc} onChange={e=>setDesc(e.target.value)} placeholder="Description" className="w-full border p-2 rounded mb-2" />
        <input value={you} onChange={e=>setYou(e.target.value)} placeholder="YouTube URL" className="w-full border p-2 rounded mb-2" />

        <select value={forAll} onChange={e=>setForAll(e.target.value)} className="w-full border p-2 rounded mb-2">
          <option value="1">All</option>
          <option value="2">Teacher</option>
          <option value="3">Student</option>
        </select>

        <select value={subj} onChange={e=>setSubj(e.target.value)} className="w-full border p-2 rounded mb-2">
          <option value="">Select Subject</option>
          {subjects.map(s => (
            <option key={s.id} value={s.id}>{JSON.parse(s.title).en}</option>
          ))}
        </select>

        <select value={lvl} onChange={e=>setLvl(e.target.value)} className="w-full border p-2 rounded mb-2">
          <option value="">Select Level</option>
          {levels.map(l => (
            <option key={l.id} value={l.id}>{JSON.parse(l.title).en}</option>
          ))}
        </select>

        <select value={stat} onChange={e=>setStat(e.target.value)} className="w-full border p-2 rounded mb-4">
          <option value="1">Active</option>
          <option value="0">Inactive</option>
        </select>

        <select value={questionType} onChange={e=>setQuestionType(e.target.value as any)} className="w-full border p-2 rounded mb-4">
          <option value="mcq">MCQ</option>
          <option value="reflection">Reflection</option>
          <option value="image">Image</option>
        </select>

{questionType === 'mcq' && (
  <div className="border p-3 rounded mb-4">
    <select
      value={mcqInputMode}
      onChange={e => setMcqInputMode(e.target.value as 'manual' | 'csv')}
      className="w-full border p-2 rounded mb-4"
    >
      <option value="manual">Upload Manually</option>
      <option value="csv">Upload via CSV</option>
    </select>

    {mcqInputMode === 'manual' && (
      <>
        {mcqList.map((q, idx) => (
          <div key={idx} className="mcq-entry">
            <textarea
              value={q.question}
              onChange={e => {
                const updated = [...mcqList];
                updated[idx].question = e.target.value;
                setMcqList(updated);
              }}
              placeholder={`Question ${idx + 1}`}
              className="w-full border p-2 rounded mb-2"
            />
            {(['a', 'b', 'c', 'd'] as const).map(opt => (
              <input
                key={opt}
                placeholder={`Option ${opt}`}
                value={q.options[opt]}
                onChange={e => {
                  const updated = [...mcqList];
                  updated[idx].options[opt] = e.target.value;
                  setMcqList(updated);
                }}
                className="w-full border p-2 rounded mb-1"
              />
            ))}
            <select
              value={q.correct_answer}
              onChange={e => {
                const updated = [...mcqList];
                updated[idx].correct_answer = e.target.value;
                setMcqList(updated);
              }}
              className="w-full border p-2 rounded"
            >
              <option value="">Select Correct</option>
              {['a', 'b', 'c', 'd'].map(opt => (
                <option key={opt} value={opt}>
                  {opt.toUpperCase()}
                </option>
              ))}
            </select>
            {mcqList.length > 1 && (
              <button onClick={() => removeMcq(idx)}>
                <IconTrash />
              </button>
            )}
          </div>
        ))}
        {mcqList.length < 5 && (
          <button onClick={addMcq} className="add-btn">
            <IconPlus /> Add another question
          </button>
        )}
      </>
    )}

    {mcqInputMode === 'csv' && (
      <div className="border p-3 rounded bg-gray-50">
        <input
          type="file"
          accept=".csv"
          onChange={handleCsvUpload}
          className="mb-2"
        />

        {/* Download Template Button */}
        <div>
  <a
    href="/MCQtemplate.csv"
    download="MCQtemplate.csv"
    className="btn btn-outline-secondary"
  >
    Download CSV Template
  </a>
</div>

      </div>
    )}
  </div>
)}

        {questionType === 'reflection' && (
          <textarea
            value={singleQ}
            onChange={e=>setSingleQ(e.target.value)}
            placeholder="Reflection question"
            className="w-full border p-2 mb-2 rounded"
          />
        )}

        {questionType === 'image' && (
          <input
            type="text"
            value={singleQ}
            onChange={e=>setSingleQ(e.target.value)}
            placeholder="Image question URL or prompt"
            className="w-full border p-2 mb-2 rounded"
          />
        )}

        {/* buttons */}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border rounded">Cancel</button>
          <button onClick={handleSave} disabled={loading} className="px-4 py-2 bg-sky-700 text-white rounded flex items-center">
            {loading && <span className="animate-spin rounded-full w-3 h-3 border-white border-t-2 mr-2" />}
            {loading? 'Saving..':'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}


interface VisionRow {
    vision_id: number
    title: string
    description: string
    youtube_url: string | null
    allow_for: 1 | 2 | 3
    subject_id?:string
    subject: string
    level: string
    level_id?:string
    status: number
    questions: QuestionPayload[]
}

export default function VisionsPage() {
    const [rows, setRows] = useState<VisionRow[]>([]);
    const [loading, setLoading] = useState(false);
  
    // Filters
    const [fStatus, setFStatus] = useState<string>('');
    const [fSubject, setFSubject] = useState<string>('');
    const [fLevel,   setFLevel]   = useState<string>('');
    // const [fType,    setFType]    = useState<string>('');
    const [expanded, setExpanded] = useState<Record<number,boolean>>({})

    // Modal states
    const [showAdd, setShowAdd] = useState(false);
    const [showEdit, setShowEdit] = useState(false);
    const [editRow, setEditRow] = useState<VisionRow | null>(null);
  
    // counts
    const totalCount = rows.length;
  
    // Fetch data
    async function fetchVisions() {
      setLoading(true);
      const params = new URLSearchParams();
      if (fStatus)  params.set('status', fStatus);
      if (fSubject) params.set('subject_id', fSubject);
      if (fLevel)   params.set('level_id', fLevel);
      // if (fType)    params.set('question_type', fType);
  
      const res = await fetch(`${api_startpoint}/api/visions?${params}`);
      const data: VisionRow[] = await res.json();
      setRows(data);
      setLoading(false);
    }
    

    const [subjects, setSubjects] = useState<any[]>([]);
    const [levels, setLevels] = useState<any[]>([]);

    useEffect(() => { 
        fetchVisions(); 
        fetch(`${api_startpoint}/api/subjects_list`, { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }, // Add this line
            body: JSON.stringify({status: '1'}) // Optional, but ensures valid POST request
          })
        .then(res => res.json())
        .then(setSubjects);

        fetch(`${api_startpoint}/api/levels`, {
            method: 'POST',
            headers: {
                "Content-Type": "application/json",
              },
            body: JSON.stringify({ page: 1 })
          })
            .then(res => res.json())
            .then(data => {
              console.log('Levels response:', data);
              setLevels(data);  // <- might need to change to setLevels(data.levels) or similar
            });

    }, [fStatus, fSubject, fLevel]);
  
    return (
        <div className={`page bg-body ${inter.className} font-sans`}>
            <Sidebar />
            <div className="page-wrapper" style={{ marginLeft: '250px' }}>
                <div className="page-body">
                    <div className="container-xl pt-4 pb-4 space-y-4">
                        <div className="card w-40">
                            <div className="card-body">
                                <div className="d-flex align-items-center">
                                    <div>
                                        <div className="subheader">Total Visions</div>
                                        <div className="h1 mb-3">
                                            <NumberFlow
                                            value={totalCount}
                                            className="fw-semi-bold text-dark"
                                            transformTiming={{endDelay:6, duration:750, easing:'cubic-bezier(0.42, 0, 0.58, 1)'}}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        {/* Filters */}
                        <div className="flex gap-4">
                            <select value={fStatus} onChange={e => setFStatus(e.target.value)}
                                    className="border p-2 rounded">
                            <option value="">All Status</option>
                            <option value="1">Active</option>
                            <option value="0">Inactive</option>
                            </select>
                            <select value={fSubject} onChange={e => setFSubject(e.target.value)}
                                    className="border p-2 rounded">
                                <option value="">All Subjects</option>
                                {subjects.map((subject) => (
                                    <option key={subject.id} value={subject.id}>  {/* Use subject.id as value */}
                                        {JSON.parse(subject.title).en}
                                    </option>
                                ))}
                            </select>
                            <select value={fLevel} onChange={e => setFLevel(e.target.value)}
                                    className="border p-2 rounded">
                                <option value="">All Levels</option>
                                {levels.map((level) => (
                                    <option key={level.id} value={level.id}>  {/* Use level.id as value */}
                                        {JSON.parse(level.title).en}
                                    </option>
                                ))}
                            </select>
                            {/* <select value={fType} onChange={e => setFType(e.target.value)}
                                    className="border p-2 rounded">
                            <option value="">All Types</option>
                            <option value="mcq">MCQ</option>
                            <option value="reflection">Reflection</option>
                            <option value="image">Image</option>
                            </select> */}

                            <button onClick={() => setShowAdd(true)}
                                    className="ml-auto bg-sky-600 text-white px-4 py-2 rounded">
                            Add Vision
                            </button>
                        </div>
                        {/* Table */}
                        {loading ? (
                            <div className="w-90 h-90 text-center">
                                <div className=' animate-spin rounded-full w-12 h-12 border-t-2 border-sky-800 text-center'></div>
                            </div>
                        ) : (
                            <table className="w-full table-auto border">
                            <thead>
                                <tr className="bg-gray-100">
                                <th className="p-2 border">Vision ID</th>
                                <th className="p-2 border">Title</th>
                                <th className="p-2 border">Description</th>
                                <th className="p-2 border">YouTube</th>
                                <th className="p-2 border">Allow For</th>
                                <th className="p-2 border">Subject</th>
                                <th className="p-2 border">Level</th>
                                <th className="p-2 border">Status</th>
                                <th className='p-2 border'>Details</th>
                                <th className="p-2 border">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map(r => (
                                  <React.Fragment key={r.vision_id}>
                                    <tr >
                                      <td className="p-2 border">{r.vision_id}</td>
                                      <td className="p-2 border">{r.title}</td>
                                      <td className="p-2 border">{r.description}</td>
                                      <td className="p-2 border">
                                      {r.youtube_url ? <a href={r.youtube_url} target="_blank">Link</a> : '-'}
                                      </td>
                                      <td className="p-2 border">
                                      {r.allow_for === 1 ? 'All' : r.allow_for === 2 ? 'Teacher' : 'Student'}
                                      </td>
                                      <td className="p-2 border">{r.subject}</td>
                                      <td className="p-2 border">{r.level}</td>
                                      <td className="p-2 border">
                                      {r.status===1?'Active':'Inactive'}
                                      </td>
                                      <td className="border p-2">
                                        <button
                                          onClick={()=>setExpanded(e=>({ ...e, [r.vision_id]: !e[r.vision_id] }))}
                                          className="text-blue-600 underline"
                                        >
                                          {expanded[r.vision_id] ? 'Hide Details' : 'Show Details'}
                                        </button>
                                      </td>
                                      <td className="p-2 border flex gap-2 justify-center">
                                        {/* Edit/Delete icons */}
                                        <IconEdit onClick={() => { setEditRow(r); setShowEdit(true);} }
                                                className="text-blue-600"/>
                                        <IconTrash onClick={async ()=>{
                                            await fetch(`${api_startpoint}/api/visions/${r.vision_id}`, {method:'DELETE'});
                                            fetchVisions();
                                        }}
                                                className="text-red-600"/>
                                      </td>
                                    </tr>

                                      {expanded[r.vision_id] && (
                                        <tr>
                                          <td colSpan={5} className="bg-gray-50 p-4">
                                            {/* List each question */}
                                            {r.questions.map(q => (
                                              <div key={q.question_id} className="mb-4 border-b pb-2">
                                                <div className="font-semibold">
                                                  [{q.question_type.toUpperCase()} Question] {q.question} 
                                                </div>
                                                {q.question_type === 'mcq' && q.options && (
                                                  <ul className="list-disc ml-6">
                                                    {Object.entries(q.options).map(([k,opt]) => (
                                                      <li key={k}>
                                                        {k.toUpperCase()}: {opt}
                                                        {q.correct_answer === k && <strong> (Correct)</strong>}
                                                      </li>
                                                    ))}
                                                  </ul>
                                                )}
                                              </div>
                                            ))}
                                          </td>
                                        </tr>
                                      )}
                                      

                                      
                                    
                                </React.Fragment>
                                ))}
                            </tbody>
                            </table>
                        )}
                        {/* Add Modal */}
                        {showAdd && (
                            <AddEditModal
                            mode="add"
                            onClose={()=>setShowAdd(false)}
                            onSuccess={()=>{setShowAdd(false); fetchVisions();}}
                            />
                        )}
                        {/* Edit Modal */}
                        {showEdit && editRow && (
                            <AddEditModal
                            mode="edit"
                            initial={editRow}
                            onClose={()=>{setShowEdit(false); setEditRow(null);}}
                            onSuccess={()=>{setShowEdit(false); fetchVisions();}}
                            />
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}