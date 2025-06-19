'use client'
import React, { useState, useEffect, useCallback, useMemo, useRef, FormEvent, ChangeEvent, ReactPortal } from 'react';
import { Inter } from 'next/font/google';
import { Sidebar } from '@/components/ui/sidebar';
import '@tabler/core/dist/css/tabler.min.css';
import NumberFlow from '@number-flow/react';
import { IconEdit, IconPlus, IconTrash, IconX } from '@tabler/icons-react';
import { ChevronDown } from 'lucide-react';
import { error } from 'console';
import Error from 'next/error';
import ReactDOM from 'react-dom';
const inter = Inter({ subsets: ['latin'] });
//const api_startpoint = 'https://lifeapp-api-vv1.vercel.app'
const api_startpoint = 'http://152.42.239.141:5000'
// const api_startpoint = 'http://152.42.239.141:5000'

interface Reference { id: number; title: string; }
interface PropTypes {
  mode: 'add' | 'edit';
  initial?: {
    id: number;
    game_type: number;
    reference_id: number;
    campaign_title: string;
    description: string;
    scheduled_for: string;
  };
  onClose: () => void;
}

export default function AddCampaignModal({
  mode, initial, onClose
}: PropTypes) : ReactPortal {
  const isEdit = mode === 'edit';
  const [title, setTitle]           = useState(initial?.campaign_title   ?? '');
  const [description, setDescription] = useState(initial?.description ?? '');
  const [gameType, setGameType]     = useState(initial?.game_type ?? 1);
  const [subjectId, setSubjectId]   = useState<number>(0);
  const [levelId, setLevelId]       = useState<number>(0);
  const [topicId, setTopicId]       = useState<number>(0);
  const [referenceId, setReferenceId] = useState(initial?.reference_id ?? 0);
  const [scheduledFor, setScheduledFor] = useState(initial?.scheduled_for ?? '');

  const [subjects, setSubjects] = useState<Reference[]>([]);
  const [levels,   setLevels]   = useState<Reference[]>([]);
  const [topics,   setTopics]   = useState<Reference[]>([]);
  const [refs,     setRefs]     = useState<Reference[]>([]);
  const [refsLoading, setRefsLoading] = useState(false);

  // load subjects & levels once
  useEffect(() => {
    fetch(`${api_startpoint}/api/subjects_list`, {
      method: 'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ status: '1' })
    })
      .then(r => r.json())
      .then(setSubjects);

    fetch(`${api_startpoint}/api/levels`, {
      method: 'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({})
    })
      .then(r => r.json())
      .then(data => setLevels(data));
  }, []);

  // load topics if quiz
  useEffect(() => {
    if (gameType !== 2) return;
    fetch(`${api_startpoint}/api/topics`, {
      method:'POST',headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ la_subject_id: subjectId, la_level_id: levelId, status: '1' })
    })
      .then(r => r.json())
      .then(setTopics);
  }, [gameType, subjectId, levelId]);

  // load refs when filters change
  useEffect(() => {
    let url = '';
    let opts: RequestInit = { method: 'GET' };

    if (gameType === 1) {
      url = `${api_startpoint}/api/mission_list`;
      opts = {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ status:1, subject_id: subjectId, level_id: levelId })
      };
    }
    else if (gameType === 2) {
      url = `${api_startpoint}/api/quiz_list`;
      opts = {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ status:1, subject_id: subjectId, level_id: levelId, topic_id: topicId })
      };
    }
    else if (gameType === 7) {
      const params = new URLSearchParams();
      params.set('status', '1');
      if (subjectId) params.set('subject_id', subjectId.toString());
      if (levelId)   params.set('level_id',   levelId.toString());
      const url = `${api_startpoint}/api/visions?${params}`;
      fetch(url)
        .then(r => r.json())
        .then((data: any[]) => {
          // ONLY grab vision_id & title
          const list = data.map(v => ({
            id:    v.vision_id,
            title: v.title
          }));
          setRefs(list);
          setReferenceId(0);
        });
    }
    
    setRefsLoading(true);
    fetch(url, opts)
      .then(r => r.json())
      .then((data: any[]) => {
        // unify shape
        const list = data.map(i => ({
          id:    i.id,
          title: i.title || i.question_title
        }));
        setRefs(list);
        setReferenceId(0);  // reset selection
      })
      
      .finally(() => {
        // stop spinner whether success or fail
        setRefsLoading(false);
      });
  }, [gameType, subjectId, levelId, topicId]);

  const handleSave = async () => {
    const payload: any = {
      title,
      description,
      game_type:    gameType,
      reference_id: referenceId,
      scheduled_for: scheduledFor
    };
    // attach filter IDs
    if (gameType === 1 || gameType === 7) {
      payload.subject_id = subjectId;
      payload.level_id   = levelId;
    }
    if (gameType === 2) {
      payload.subject_id = subjectId;
      payload.level_id   = levelId;
      payload.topic_id   = topicId;
    }

    const url    = isEdit ? `${api_startpoint}/api/campaigns/${initial!.id}` : `${api_startpoint}/api/campaigns`;
    const method = isEdit ? 'PUT' : 'POST';

    const res = await fetch(url, {
      method,
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });

    if (res.ok) onClose();
    else        alert('Error saving campaign');
  };

  const modalContent = (
    <div className="modal-backdrop fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999
    }}
      >
      <div 
      style={{
        background: 'white',
        padding: 24,
        borderRadius: 8,
        maxWidth: 400,
        width: '100%',
        // NEW:
        maxHeight: '90vh',      // never taller than 80% of the viewport
        overflowY: 'auto',      // scroll if content overflows
      }}
      >
      <div className="modal-dialog modal-sm">
      <div className="modal-content">
        <h2 className="text-xl mb-4">
          {isEdit ? 'Edit Campaign' : 'Add Campaign'}
        </h2>

        <label className="block mb-2">Title</label>
        <input
          className="input mb-3 w-full border p-2 rounded"
          value={title} onChange={e => setTitle(e.target.value)}
          
        />

        <label className="block mb-2">Description</label>
        <textarea
          className="textarea mb-3 w-full border p-2 rounded"
          value={description}
          onChange={e => setDescription(e.target.value)}
        />

        <label className="block mb-2">Game Type</label>
        <select
          className="select mb-3 w-full border p-2 rounded"
          value={gameType}
          onChange={e => setGameType(+e.target.value)}
        >
          <option value={1}>Mission</option>
          <option value={2}>Quiz</option>
          <option value={7}>Vision</option>
        </select>

        {/* Subject + Level filters */}
        {(gameType === 1 || gameType === 2 || gameType === 7) && (
          <>
            <label className="block mb-1">Subject</label>
            <select
              className="select mb-3 w-full border p-2 rounded"
              value={subjectId}
              onChange={e => setSubjectId(+e.target.value)}
            >
              <option value={0}>Select Subject</option>
              {subjects.map(s =>
                <option key={s.id} value={s.id}>{JSON.parse(s.title).en}</option>
              )}
            </select>

            <label className="block mb-1">Level</label>
            <select
              className="select mb-3 w-full border p-2 rounded"
              value={levelId}
              onChange={e => setLevelId(+e.target.value)}
            >
              <option value={0}>Select Level</option>
              {levels.map(l =>
                <option key={l.id} value={l.id}>{JSON.parse(l.title).en}</option>
              )}
            </select>
          </>
        )}

        {/* Topic filter for Quiz */}
        {gameType === 2 && (
          <>
            <label className="block mb-1">Topic/Set</label>
            <select
              className="select mb-3 w-full border p-2 rounded"
              value={topicId}
              onChange={e => setTopicId(+e.target.value)}
            >
              <option value={0}>Select Topic</option>
              {topics.map(t =>
                <option key={t.id} value={t.id}>{JSON.parse(t.title).en}</option>
              )}
            </select>
          </>
        )}

        {/* Dynamic Reference dropdown */}
        <label className="block mb-1">
          {gameType === 1 ? 'Select Mission' :
           gameType === 2 ? 'Select Quiz' :
           'Select Vision'}
        </label>
        {refsLoading ? (
          <div className='animate-spin rounded-full border-sky-800 border-t-2 w-3 h-3'></div>
        ): (
          <select
            className="select mb-3 w-full border p-2 rounded"
            value={referenceId}
            onChange={e => setReferenceId(+e.target.value)}
          >
            <option value={0}>-- choose --</option>
            {refs.map(r =>
              <option key={r.id} value={r.id}>{r.title}</option>
            )}
          </select>
        )}
        

        {/* Schedule date */}
        <label className="block mb-2">Schedule Date</label>
        <input
          className="input mb-4 w-full border p-2 rounded"
          type="date"
          value={scheduledFor}
          onChange={e => setScheduledFor(e.target.value)}
        />

        <div className="flex justify-end gap-2">
          <button
            className="btn btn-secondary"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={!referenceId || !title || !scheduledFor}
          >
            Save
          </button>
        </div>
      </div>
      </div>
      </div>
    </div>
  );
  return ReactDOM.createPortal(modalContent, document.body);
}