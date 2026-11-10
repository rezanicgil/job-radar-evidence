import assert from 'node:assert/strict';
import {durationConstraintNote as note} from '../releases/static-space/duration-constraints.js';
for(const [text,kind] of [
  ['Deployed a change to production in the past 30 days.', 'Recent work'],
  ['Son 30 gün içinde bir sürümü canlıya aldım.', 'Recent work'],
  ['8+ years of testing experience with at least 5 years in test automation.', 'Multiple durations'],
  ['Yazılım testinde 8 yıl deneyim ve otomasyonda 5 yıl deneyim.', 'Multiple durations'],
  ['0–2 years of software development experience', 'Experience range'],
  ['En fazla üç yıl deneyim', 'Upper limit'],
  ['Minimum 3 years of backend experience', null],
  ['We offer 30 days of leave.', null],
  ['Experience with the last 30 releases', null]
])assert.equal(note(text)?.split(' · ')[0]??null,kind,text);
