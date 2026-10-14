import { Component, signal } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';

declare global {
  interface Window { NativeStore: { invoke<T>(name: string, args: Record<string, unknown>): Promise<T> }; }
}

@Component({
  selector: 'ns-greeting',
  standalone: true,
  template: `<label for="angular-name">Your name</label>
    <input id="angular-name" #name maxlength="80">
    <button type="button" (click)="greet(name.value)" [disabled]="busy()">Say hello</button>
    <p aria-live="polite">{{ message() }}</p>`
})
class Greeting {
  message = signal('');
  busy = signal(false);
  async greet(name: string) {
    this.busy.set(true);
    try {
      const result = await window.NativeStore.invoke<{message: string}>('greet_person', {name});
      this.message.set(result.message);
    } catch {
      this.message.set('Enter a name between 1 and 80 characters.');
    } finally { this.busy.set(false); }
  }
}
bootstrapApplication(Greeting).catch(console.error);
